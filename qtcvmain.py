# from Python
import sys
import math

# Image processing necessities
import cv
import cv2
import numpy as np
from PIL import Image

# GUI from PyQt4
from PyQt4 import QtCore, QtGui, uic


# Video (WebCam) Class
class Video(QtCore.QObject):
    """Video Class"""

    def __init__(self, captureDevice=0):
        # Initializing the parent class
        QtCore.QObject.__init__(self)

        # Set Camera Properties
        self.capture = cv2.VideoCapture(captureDevice)
        self.capture.set(cv.CV_CAP_PROP_FRAME_WIDTH, 640);
        self.capture.set(cv.CV_CAP_PROP_FRAME_HEIGHT, 480);
        self.capture.set(cv.CV_CAP_PROP_BRIGHTNESS, 10);
        self.capture.set(cv.CV_CAP_PROP_EXPOSURE, 10);

        # Current/Previous frames
        self.currentFrame = np.array([])
        self.previousFrame = np.array([])

        # laser Template for matchTemplate`s algorithm
        #   we may use a template image to find the lase spot better
        #   together with HoughCircles to find the laset spot as a cicle
        #   and the center of the brightest spot
        self.laserTemplate = cv2.imread("lase_spot.jpg")

        # Target (Circle)
        self.target = dict(x=320, y=240, radius=175)

        # Bullets
        self.bullets = []
        self.bulletCalibre = 4.5


    def captureNextFrame(self):
        """capture frame and reverse RBG BGR and return opencv image"""

        # read frame from webcam
        success, readFrame=self.capture.read()

        # if a frame was retrieved successfully
        if success==True:

            # Convert BGR to HSV (Hue/Saturation/Value) channel and split them
            hsv_img = cv2.cvtColor(readFrame, cv.CV_BGR2HSV)
            h, s, v = cv2.split(hsv_img)

            # NOT NECESSARY, SO COMMENTED:
            # Extract Value channel from Hue-Saturation-Value image
            #     value_channel = Image.fromarray(v)
            #     valueImage = np.array(value_channel)
            valueArray = np.array(v)
            hueArray = np.array(h)
            saturationArray = np.array(s)

            # Apply Threshold for Laser Brightness on valueImage
            retval, valueArrayThresholded = cv2.threshold(src=valueArray, thresh=240, maxval=255, type=cv2.THRESH_BINARY)
            valueImageThresholded = cv2.merge([valueArrayThresholded, valueArrayThresholded, valueArrayThresholded])

            # TODO: complete template detection
            # Find Laser Spot using matchTemplate
            # try:
            #   matchTemplateResult = cv2.matchTemplate(image=readFrame, templ=self.laserTemplate, method=cv2.TM_CCOEFF)
            #   (_, _, templateMinLoc, templateMaxLoc) = cv2.minMaxLoc(matchTemplateResult)
            #   cv2.circle(readFrame, (templateMaxLoc[0]+27, templateMaxLoc[1]+35), 25, 100, 1)
            #   print "minLoc:%s maxLoc:%s" % (templateMinLoc, templateMaxLoc)
            # except:
            #   pass

            # Find Circles in GreyScaled valueImageThresholded
            valueGreyImage = cv2.cvtColor(valueImageThresholded, cv2.COLOR_BGR2GRAY)
            found_circles = cv2.HoughCircles(valueGreyImage, method=cv.CV_HOUGH_GRADIENT, dp=1, minDist=10, minRadius=10) #, maxRadius=50, param1=50, param2=7
            if found_circles is not None:
              for circles in found_circles:
                for circle in circles:
                  # Draw Circle around found Circles on the original Frame
                  cv2.circle(img=readFrame, center=(circle[0], circle[1]), radius=circle[2], color=100, thickness=1)

                  # Add Candidated Circle to bullets hit list
                  # self.bullets.append((circle[0], circle[1]))

                  # Emits laserDetected Signal
                  # self.emit(QtCore.SIGNAL("laserDetected(PyQt_PyObject, PyQt_PyObject)"), (circle[0], circle[1]), 0)


            # Find Max Value as lase spot
            f = cv.fromarray(valueArrayThresholded)
            minVal, maxVal, minLoc, maxLoc = cv.MinMaxLoc(f)

            # if pixel`s color value is greater than this number, it's laser pointer spot
            if maxVal > 254.0:

              # Add the location of maxVal to bullets hit list
              self.bullets.append(maxLoc)

              # Emits laserDetected Signal
              self.emit(QtCore.SIGNAL("laserDetected(PyQt_PyObject, PyQt_PyObject)"), maxLoc, maxVal)
              pass

            # Draw Circle around bullets hit
            for bullet in self.bullets:
              # FIXME: radius can't be float
              cv2.circle(img=readFrame, center=bullet, radius=int(self.bulletCalibre), color=(255, 100, 100), thickness=-1)

            # draw Semi-Transparent Target in original frame`s clone
            readFrame2 = readFrame.copy()
            cv2.circle(img=readFrame2, center=(self.target['x'], self.target['y']), radius=self.target['radius'], color=100, thickness=-1)
            finalImage = cv2.addWeighted(src1=readFrame, alpha=1, src2=readFrame2, beta=0.5, gamma=0)

            # sets finalImage as current image
            self.currentFrame = finalImage

    def convertFrame(self):
        """converts the captured frame to QtGui.QPixmap"""
        try:
            # Get video`s hight/width from currentFrame (NumpyArray)
            height,width=self.currentFrame.shape[:2]

            # Convert NumpyArray from BGR to RGB Image
            img=QtGui.QImage(self.currentFrame,
                              width,
                              height,
                              QtGui.QImage.Format_RGB888)

            # RGB Image to QPixmap
            img=QtGui.QPixmap.fromImage(img)

            # Preserve the current frame as the now previous frame
            self.previousFrame = self.currentFrame

            # Return the QPixmap object
            return img
        except:
            return None


# MainWindow GUI Class
class Gui(QtGui.QMainWindow):
    def __init__(self,parent=None):
        QtGui.QWidget.__init__(self,parent)

        # Current Score and number of hits
        self.hits = 0
        self.total = 0

        # Loads UI created using QtDesigner
        self.ui = uic.loadUi('mainWindow.ui', self)

        # initialize Video Instance (captureDevice=0)
        self.video = Video()

        # FIXME: Very Bad IDEA! use signals on video to inform frame is ready
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self.play)
        self._timer.start(0.1)
        self.update()

        # Qt4 GUI SIGNAL/SLOT connections
        self.ui.adjustTargetUp.clicked.connect(self.adjustCircleUp)
        self.ui.adjustTargetDown.clicked.connect(self.adjustCircleDown)
        self.ui.adjustTargetLeft.clicked.connect(self.adjustCircleLeft)
        self.ui.adjustTargetRight.clicked.connect(self.adjustCircleRight)
        self.ui.adjustTargetSizeUp.clicked.connect(self.adjustCircleSizeUp)
        self.ui.adjustTargetSizeDown.clicked.connect(self.adjustCircleSizeDown)
        self.ui.resetBtn.clicked.connect(self.resetClicked)
        self.ui.PictureBtn.clicked.connect(self.PictureClicked)
        self.ui.caliberEdit.valueChanged.connect(self.adjustBulletCaliber)
        QtCore.QObject.connect(self.video,
                       QtCore.SIGNAL("laserDetected(PyQt_PyObject, PyQt_PyObject)"),
                       self.laserDetected)

    def resetClicked(self):
      self.video.bullets = []
      self.hits = 0
      self.total = 0
      self.ui.hitsLabel.setText("%s" % self.hits)
      self.ui.pointsLabel.setText("%s" % 0)
      self.ui.totalLabel.setText("%s" % self.total)

    def laserDetected(self, loc, value):
      global circle_x, circle_y, circle_radius
      distance = math.hypot(loc[0] - circle_x, loc[1] - circle_y)
      score_distance = circle_radius / 6

      point = 10 - math.floor(distance/score_distance)
      if point > 4:
        self.hits += 1
        self.total += point
      else:
        self.hits += 1
        point = "Missed"
      print "point:%s\thits:%s\ttotal:%s" % (point, self.hits, self.total)
      self.ui.hitsLabel.setText("%s" % self.hits)
      self.ui.pointsLabel.setText("%s" % point)
      self.ui.totalLabel.setText("%s" % self.total)

    def adjustCircleUp(self):
      self.video.target['y'] -= 5

    def adjustCircleDown(self):
      self.video.target['y'] += 5

    def adjustCircleLeft(self):
      self.video.target['x'] -= 5

    def adjustCircleRight(self):
      self.video.target['x'] += 5

    def adjustCircleSizeUp(self):
      self.video.target['radius'] += 5

    def adjustCircleSizeDown(self):
      self.video.target['radius'] -= 5

    def adjustBulletCaliber(self, caliber):
      # TODO: this should be calculated according to the distance provided
      self.video.bulletCalibre = caliber

    def PictureClicked(self):
      cv2.imwrite("screen_shot.jpg", self.video.currentFrame);

    def play(self):
        try:
            # FIXME: it's probably causing blocking the GUI
            #        use video as a thread an sends signals on frameReady
            self.video.captureNextFrame()
            self.ui.videoFrame.setPixmap(self.video.convertFrame())
            self.ui.videoFrame.setScaledContents(True)
        except TypeError:
            # FIXME: Hmm?!
            pass


def main():
    # Creates Qt Application
    app = QtGui.QApplication(sys.argv)

    # show MainWindow GUI
    ex = Gui()
    ex.show()

    # loops until the application exits
    sys.exit(app.exec_())

# Run GUI when the script executed directly
if __name__ == '__main__':
    main()
