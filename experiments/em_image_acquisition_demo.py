import time
import wx
import threading
from pubsub import pub

# A little demo showing a worker thread (mimicking EM image acquisition) running in the background
# while the UI remains responsive and provides user feedback. The worker thread can be paused/resumed,
# and stopped early as well.

# High prio:
# IMPROVEME: ensure that the status text is always nicely centered horizontally
# IMPROVEME: add confirmation dialog when user presses Stop
# IMPROVEME: close window when user pressed Stop?
# IMPROVEME: what to do when image acquisition ends normally?

# Low prio:
# IMPROVEME: add auto-pause functionality (?)
# IMPROVEME: allow user to press Stop while paused as well (we currently avoid that because the worker thread
# is a bit more complicated to implement in that case)
# IMPROVEME: add remaining imaging time estimate


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
                print 'Start acquiring EM image {}'.format(i)
                time.sleep(3)
                print 'Done'

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

class AcquisitionDialog(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, "EM Image Acquisition", style=wx.DEFAULT_FRAME_STYLE & (~wx.CLOSE_BOX))

        # Add a panel so it looks the correct on all platforms
        panel = wx.Panel(self, wx.ID_ANY)

        self.num_images = 7

        self.worker = AcquisitionThread(self.num_images)

        self.progress_bar = wx.Gauge(parent=panel, size=(200,-1), range=self.num_images)

        self.status = wx.StaticText(panel, label="", size=(200,-1), style=wx.ALIGN_CENTER_HORIZONTAL)

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
        self.status.SetLabel("Finishing current image acquisition")
        self.worker.stop()

    def do_pause(self):
        # When we ask the worker thread to pause, it will still finish acquiring the image it is working on.
        # To avoid user confusion, we provide feedback that we received his/her request to pause, and temporarily
        # disable the pause/resume button (to avoid receiving repeated clicks from impatient users).
        self.status.SetLabel("Finishing current image acquisition")
        self.pause_resume_button.Enable(False)
        self.stop_button.Enable(False)
        wx.Yield()  # have wxPython update the GUI *immediately*

        self.worker.pause()
        self.status.SetLabel("Paused")
        self.pause_resume_button.SetLabel("Resume")
        self.pause_resume_button.Enable(True)

    def do_resume(self):
        self.worker.resume()
        self.status.SetLabel("Acquiring images")
        self.pause_resume_button.SetLabel("Pause")
        self.stop_button.Enable(True)

    def handle_acquiring_msg(self, nr):
        self.status.SetLabel('Acquiring image {} / {}'.format(nr, self.num_images))
        self.progress_bar.SetValue(nr)

    def handle_done_msg(self, stopped):
        self.status.SetLabel("Image acquisition stopped by user." if stopped else "All images acquired.")
        self.pause_resume_button.Enable(False)
        self.stop_button.Enable(False)

    def start_acquiring(self):
        print("Starting acquisition")
        self.worker.start()

if __name__ == "__main__":
    app = wx.App(False)
    dialog = AcquisitionDialog()
    dialog.Show()
    dialog.start_acquiring()
    app.MainLoop()
