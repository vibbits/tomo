import time
import wx
import threading
from pubsub import pub

# A little demo showing a worker thread (mimicking EM image acquisition) running in the background
# while the UI remains responsive and provides user feedback. The worker thread can be paused/resumed,
# and stopped early as well.

# Possible improvements:
# TODO: allow user to Stop while imaging is paused
# TODO: add auto-pause functionality (?)
# TODO: add remaining imaging time estimate


# Messages that will be sent via pubsub
MSG_DONE = "done"
MSG_ACQUIRING = "acquiring"


class AcquisitionThread(threading.Thread):
    # Based on https://stackoverflow.com/questions/33640283/thread-that-i-can-pause-and-resume

    def __init__(self, num_images):
        threading.Thread.__init__(self)
        self.num_images = num_images
        self.stopped = False
        self.paused = False
        self.paused_condition = threading.Condition(threading.Lock())

    def run(self):
        i = 1
        with self.paused_condition:
            while i <= self.num_images:
                while self.paused:
                    # User wants to pause imaging,
                    # wait until notify is called (which is when user does resume).
                    self.paused_condition.wait()

                if self.stopped:
                    # user wants to abort imaging
                    break

                wx.CallAfter(pub.sendMessage, MSG_ACQUIRING, nr=i)
                self.acquire_image(i)

                i += 1

        wx.CallAfter(pub.sendMessage, MSG_DONE, stopped=self.stopped)

    def acquire_image(self, i):
        print 'Start acquiring image {}'.format(i)
        time.sleep(3)
        print 'Done acquiring image {}'.format(i)

    def pause(self):
        print('Thread: pause')
        self.paused = True
        self.paused_condition.acquire()

    def resume(self):
        print('Thread: resume')
        self.paused = False
        self.paused_condition.notify()
        self.paused_condition.release()

    def stop(self):
        print('Thread: stop')
        assert self.is_paused()
        # Imaging is currently paused. Have it continue again but with the 'stopped' flag set,
        # so it will then terminate the imaging cycle as soon as possible.
        # TODO: This is a bit odd. It would be nicer if we could also stop when imaging is still ongoing.
        self.stopped = True
        self.resume()

    def is_paused(self):
        return self.paused


class StopWatch:
    def __init__(self):
        """Create a stopwatch. It does not automatically start."""
        self.running = False
        self.elapsed = 0
        self.time_last_start = 0

    def start(self):
        """Start the stopwatch (or resume after a stop). Has no effect if already running."""
        if not self.running:
            self.running = True
            self.time_last_start = time.time()

    def stop(self):
        """Stop the stopwatch. Has no effect if not running."""
        if self.running:
            self.running = False
            self.elapsed += (time.time() - self.time_last_start)

    def reset(self):
        """Reset the stopwatch to not running and no time passed."""
        self.running = False
        self.elapsed = 0
        self.time_last_start = 0

    def elapsed_time(self):
        """Return the time elapsed (in seconds) while the StopWatch was actually running,
        so not including the time when it was stopped."""
        if self.running:
            return self.elapsed + (time.time() - self.time_last_start)
        else:
            return self.elapsed


class AcquisitionDialog(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, "EM Image Acquisition", size=(400,-1), style=wx.DEFAULT_FRAME_STYLE & (~wx.CLOSE_BOX))
        # note: we suppress the dialog close button, to avoid closing the dialog with the worker thread still running.

        # Add a panel so it looks the correct on all platforms (not sure if required, copied from example code)
        panel = wx.Panel(self, wx.ID_ANY)

        self.num_images = 7
        self.stopwatch = StopWatch()

        self.worker = AcquisitionThread(self.num_images)

        self.progress_bar = wx.Gauge(parent=panel, size=(350,-1), range=self.num_images)

        self.status = wx.StaticText(panel, style=wx.ALIGN_CENTER_HORIZONTAL)

        self.stop_button = wx.Button(panel, label="Stop")
        self.stop_button.Bind(wx.EVT_BUTTON, self.on_stop_button_pressed)

        self.pause_resume_button = wx.Button(panel, label="Pause")
        self.pause_resume_button.Bind(wx.EVT_BUTTON, self.on_pause_resume_button_pressed)

        self.pause_resume_button.SetFocus()

        bs = wx.BoxSizer(wx.HORIZONTAL)
        bs.Add(self.stop_button, 0, wx.ALL | wx.CENTER, 5)
        bs.AddSpacer(40)
        bs.Add(self.pause_resume_button, 0, wx.ALL | wx.CENTER, 5)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.status, 0, wx.ALL | wx.CENTER, 5)
        sizer.Add(self.progress_bar, 0, wx.ALL | wx.CENTER, 5)
        sizer.Add(bs, 0, wx.ALL | wx.CENTER, 5)
        panel.SetSizer(sizer)

        sizer.Fit(self)

        self.CentreOnScreen()

        # Subscribe to messages from the worker thread that does the imaging.
        pub.subscribe(self.handle_acquiring_msg, MSG_ACQUIRING)
        pub.subscribe(self.handle_done_msg, MSG_DONE)

    def on_pause_resume_button_pressed(self, event):
        if self.pause_resume_button.GetLabel() == "Pause":
            self.do_pause()
        else:
            self.do_resume()

    def on_stop_button_pressed(self, event):
        print("Stop button clicked")

        # Start by pausing the imaging task
        assert not self.worker.is_paused()
        self.do_pause()

        # Ask for user confirmation to really abort imaging.
        # If the user changes her mind, we can resume imaging.
        with wx.MessageDialog(None, "Stop EM image acquisition immediately?", style=wx.YES | wx.NO) as dlg:
            if dlg.ShowModal() == wx.ID_YES:
                self.do_stop()
            else:
                self.do_resume()

    def do_start(self):
        self.stopwatch.start()
        self.worker.start()

    def do_stop(self):
        self.worker.stop()
        self.stopwatch.stop()

    def do_pause(self):
        # When we ask the worker thread to pause, it will still finish acquiring the image it is working on.
        # To avoid user confusion, we provide feedback that we received his/her request to pause, and temporarily
        # disable the pause/resume button (to avoid receiving repeated clicks from impatient users).
        self.set_status("Finishing current image acquisition")

        self.pause_resume_button.Enable(False)
        self.stop_button.Enable(False)
        wx.Yield()  # have wxPython update the GUI *immediately*

        self.worker.pause()
        self.set_status("Paused")

        self.pause_resume_button.SetLabel("Resume")
        self.pause_resume_button.Enable(True)

        self.stopwatch.stop()

    def do_resume(self):
        self.stopwatch.start()
        self.worker.resume()
        self.pause_resume_button.SetLabel("Pause")
        self.stop_button.Enable(True)

    def handle_acquiring_msg(self, nr):
        self.set_status('Acquiring image {} / {}'.format(nr, self.num_images))
        self.progress_bar.SetValue(nr)

    def handle_done_msg(self, stopped):
        message = "Image acquisition stopped by user." if stopped else "Done! All images were acquired."
        wx.MessageBox(message, "", wx.OK | wx.CENTRE, self)
        self.Close()

    def set_status(self, text):
        self.status.SetLabel(text)
        self.status.GetParent().Layout()  # Since the size of the StaticText changed, the layout needs to be updated

    def start_acquiring(self):
        print("Starting EM image acquisition")
        self.do_start()


if __name__ == "__main__":
    app = wx.App(False)
    dialog = AcquisitionDialog()
    dialog.Show()
    dialog.start_acquiring()
    app.MainLoop()
