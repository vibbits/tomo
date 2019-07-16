import time
import wx
import threading
from pubsub import pub

# A little demo showing a worker thread (mimicking EM image acquisition) running in the background
# while the UI remains responsive and provides user feedback. The worker thread can be paused/resumed,
# and stopped early as well.

# High prio:
# TODO: implement Stop; allow user to Stop while paused as well as when running

# Low prio:
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

        # The pause_cond contition variable is used to synchronize between the even processing thread of wxpython and
        # this worker thread that does the image acquisition.
        self.paused = False
        self.pause_cond = threading.Condition(threading.Lock())

    def run(self):
        i = 1
        with self.pause_cond:
            while i <= self.num_images:
                while self.paused:
                    self.pause_cond.wait()  # release lock, and block until notify(), then re-acquire the lock

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
        self.pause_cond.acquire()  # If lock is locked then block until it is released. Afterwards lock and return.

    def resume(self):
        print('Thread: resume')
        self.paused = False
        self.pause_cond.notify()  # notify, so thread will wake after lock is released
        self.pause_cond.release()  # release the lock and return (if lock is not locked: runtimeerror!)

    def stop(self):
        print('Thread: stop')
        assert self.paused
        # self.stopped = True
        # XXXXX

    def is_paused(self):
        return self.paused  # CHECKME: is this safe? or do we need pause_cond?


class AcquisitionDialog(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, "EM Image Acquisition", size=(400,-1), style=wx.DEFAULT_FRAME_STYLE & (~wx.CLOSE_BOX))
        # note: we suppress the dialog close button, to avoid closing the dialog with the worker thread still running.

        # Add a panel so it looks the correct on all platforms (not sure if required, copied from example code)
        panel = wx.Panel(self, wx.ID_ANY)

        self.num_images = 3

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

        # Subscribe to messages from the worker thread
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

    def do_resume(self):
        self.worker.resume()
        self.pause_resume_button.SetLabel("Pause")
        self.stop_button.Enable(True)

    def do_stop(self):
        self.worker.stop()

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
        self.worker.start()


if __name__ == "__main__":
    app = wx.App(False)
    dialog = AcquisitionDialog()
    dialog.Show()
    dialog.start_acquiring()
    app.MainLoop()
