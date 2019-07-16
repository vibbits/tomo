import time
import wx
import threading
from pubsub import pub

# A little demo showing a worker thread (mimicking EM image acquisition) running in the background
# while the UI remains responsive and provides user feedback. The worker thread can be paused/resumed,
# and stopped early as well.

# High prio:
# TODO: implement Stop
# TODO: add confirmation dialog when user presses Stop

# Low prio:
# TODO: add auto-pause functionality (?)
# TODO: allow user to press Stop while paused as well (we currently avoid that because the worker thread
# is a bit more complicated to implement in that case)
# TODO: add remaining imaging time estimate


class AcquisitionThread(threading.Thread):
    # Based on https://stackoverflow.com/questions/33640283/thread-that-i-can-pause-and-resume

    def __init__(self, num_images):
        threading.Thread.__init__(self)
        self.num_images = num_images
        self.paused = False
        self.stopped = False
        self.pause_cond = threading.Condition(threading.Lock())

    def run(self):
        i = 1
        while i <= self.num_images and not self.stopped:
            with self.pause_cond:
                while self.paused:
                    self.pause_cond.wait()

                wx.CallAfter(pub.sendMessage, "acquiring", nr=i)
                print 'Start acquiring image {}'.format(i)
                time.sleep(3)
                print 'Done acquiring image {}'.format(i)

                i += 1

        wx.CallAfter(pub.sendMessage, "done", stopped=self.stopped)

    def pause(self):
        print('Thread: pause')
        self.paused = True
        self.pause_cond.acquire()

    def resume(self):
        print('Thread: resume')
        self.paused = False
        self.pause_cond.notify()  # notify, so thread will wake after lock is released
        self.pause_cond.release()  # release the lock

    def stop(self):
        print('Thread: stop')
        assert not self.paused
        self.stopped = True

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

        # subscribe to messages from the worker thread
        pub.subscribe(self.handle_acquiring_msg, "acquiring")
        pub.subscribe(self.handle_done_msg, "done")

    def on_pause_resume_button_pressed(self, event):
        if self.pause_resume_button.GetLabel() == "Pause":
            self.do_pause()
        else:
            self.do_resume()

    def on_stop_button_pressed(self, event):
        print("Stop button clicked")
        # # FIXME: at this point, the worker thread will still happily continue imaging, while the user
        # # is reading the confirmation dialog. But we cannot totally stop the thread because the user might
        # # change his mind. So we probably need to pause it (unless it is paused already!)
        # with wx.MessageDialog(None, "Stop EM image acquisition immediately?", style=wx.YES | wx.NO) as dlg:
        #     if not self.worker.is_paused():
        #         self.worker.do_
        #     if dlg.ShowModal() == wx.ID_YES:
        #         pass # FIXME: implement! How precisely? resume and immediately stop (unless we can stop while being paused...)
        #     else:
        #         pass # resume

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
