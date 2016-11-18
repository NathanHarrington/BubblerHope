#!/usr/bin/env python
'''
The Bubbler - be memorable. 

Created by Harrington Digital productions:
harrington.nathan@gmail.com
Nathan - implementation
Jeanette, Elena, Alexander, Daniel, Elise, Meaghan, Sean - ideas and testing

Python application that uses a webcam, opencv, and drawing primitives to provide
a simple game with real time visual effects. 

Demonstration video:
        https://plus.google.com/100412424991063551562/posts/44P4AdePH3c

Requirements:
        Python (x,y) 2.7.5.1 with PyOpenCv 
        usb webcam

Developed on:
        Windows 8/8.1/7
        Lenovo IdeaPad U430 Intel core i4-4200U 1.6Ghz 4GB RAM
        Logitech C920 

Usage:
        python -u Bubbler.py
        (clear the playing area first, start when the countdown ends )
        
Detailed usage instructions:
Install python (x,y), during the installation process, make sure pyopencv is
selected.

Install the C920 hardware and control software.

For extended gameplay, connect the control computer to a large screen display
(larger screens make everyone happy). Use a wireless keyboard for control. The
operator should position himself where he can see the computer main display as
well as the extended display on the large screen. This can be done by purchasing
long hdmi cables and usb-extended cables to work with the logitech camera.

Start the logitech camera application, position the camera to show an empty
room. Critical factors to include when choosing a playing area:
        Ensure contrast between actors and non-actors: Do the kids have the same
        shirt color as the couch?

        Make sure the camera will not be moved.
        Make sure nothing in the background will be moved.

Once the camera has been positioned, use the logitech camera advanced control
settings and turn off any auto management of the camera. This includes auto
focus, gain, exposure, color management, etc.

Close the logitech camera application and settings.

With the camera pointed at the empty playing area, Start the Bubbler in video
only mode for application configuration:
        python -u Bubbler.py --video-only

You should see two windows appear, one all black with a frames per second
designator, and another which shows the view of the camera. Engage an actor to
walk through the camera's view. Now that the playing environment is setup, close
the Bubbler (press 'q' or 'esc' ), and restart in game mode:
        python -u Bubbler.py

A countdown will be shown. During this initial setup process, the reference
image for the whole game will be acquired. Anything that changes in the scene
will be computed as motion. This includes shadows on the wall; indentations on
the couch for when a kid sat down, then moved; adults lurking in the doorways;
throw rugs moved during play. Anything that moves is motion.

During the game you can clear the playing area and press the 'r' key to take a
new reference image.

Game design:
    Get the highest score possible in the time allotted. Every gameplay decision
is based on the idea that most kids enjoying gaming the system as much as the
gameplay itself. That's why the mess bubbles time out. That's why it's harder to
get a high score by just leaving your arm visible to the window. Game scores are
not recorded anywhere to encourage spectators to track the highest score, as
well as establishing classes of ability - if you're a huge adult, it's harder to
avoid the bubbles - but it's easier to hit the blue ones too.

Alternative play mode ideas:
    Position the camera where just hands are visible. Or just feet.
    Place a chair with a zoomed in view of just a face.

'''  
import cv2, sys, logging, Queue, random, time, numpy, optparse
from PyQt4.QtGui import *
from PyQt4.QtCore import *

import video
from common import draw_str, small_draw_str, big_draw_str

IMG_WIDTH  = 800
IMG_HEIGHT = 600
DEBUG      = False 
VIDEO_ONLY = False

class ReferenceMAT(object):
    def __init__(self):
        logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
            level=logging.DEBUG)
        self.log = logging.getLogger()
        self.reference_color = None
        self.reference_gray  = None
        self.preproc_enabled = False

    def pre_process(self, in_mat, in_motion_mat):
        self.log.info("New reference acquisition")
        self.reference_color = in_mat.copy()
        self.reference_gray  = cv2.cvtColor(self.reference_color, 
                                            cv2.COLOR_BGR2GRAY)
        return in_mat, in_motion_mat


class DebugInfo(object):
    def __init__(self):
        self.last_time = cv2.getTickCount()
        self.tick_frequency = cv2.getTickFrequency()
        self.enabled = True
        
    def opencv_fps(self):
        now = cv2.getTickCount()
        dt = (now - self.last_time) / self.tick_frequency
        self.last_time = now
        return 1/dt

    def post_process(self, in_mat, in_motion_mat):
        result = big_draw_str(in_motion_mat, (IMG_WIDTH-180,50), 
                'FPS: %0.0f' % self.opencv_fps())


class GameControl(object):
    def __init__(self):
        self.enabled = True

        class signalObject(QObject):
             start_game = pyqtSignal()
             stop_game  = pyqtSignal()
        self.game_sig = signalObject()

        self.reset_game()

        # On initial startup, have a shorter delay
        self.setup_game_total_prestart_time = 3
        self.prestart_time = self.setup_game_total_prestart_time

    # In addition to all of the game control variables, this will create a
    # countdown for an auto game startup and then restart repeatedly
    def reset_game(self):
        self.high_score = 0

        self.score = 0
        self.high_score = 0
        self.score_interval = 100
        self.good_radius = 20
        self.good_increment = IMG_HEIGHT / 48  

        self.base_radius = 10
        self.bad_radius = self.base_radius
        self.bad_radius_jump = 10
        self.bad_exists = 0
        self.bad_increment = IMG_HEIGHT / 48 
        self.bad_multi = 10
        self.score_level = 100
        self.max_bubbles = 10

        self.popped_increment = 3
        self.popped_radius = 2

        self.max_choppers = 1
        self.show_chop_duration = 60

        self.max_smooshers = 1
        self.show_smoosh_duration = 10
    
        self.time_x = 0
        self.time_y = IMG_HEIGHT - 10
        self.game_total_time = 60
        if DEBUG:
            self.game_total_time = 10
        self.time_left = self.game_total_time

        self.prestart_time_x = (IMG_WIDTH / 2) -80
        self.prestart_time_y = (IMG_HEIGHT /2)
        self.game_total_prestart_time = 10
        if DEBUG:
            self.game_total_prestart_time = 2
        self.prestart_time = self.game_total_prestart_time

        self.delay_start_timer = QTimer()
        self.delay_start_timer.setSingleShot(True)
        self.delay_start_timer.timeout.connect(self.delay_start)
        self.delay_start_timer.start(0)

        self.game_timer = QTimer()
        self.game_timer.setSingleShot(True)
        self.game_timer.timeout.connect(self.time_update)

    def delay_start(self):
        self.prestart_time -= 1
        if self.prestart_time >= 0:
            self.delay_start_timer.start(1000)
        else:
            self.game_timer.start(0)
            self.game_sig.start_game.emit()

    def time_update(self):
        self.time_left -= 1
        
        if self.time_left <= 0:
            self.time_left = self.game_total_time
            self.prestart_time = self.game_total_prestart_time
            self.delay_start_timer.start(0)
            self.game_sig.stop_game.emit()
            self.reset_game()
        else:
            self.game_timer.start(1000)

    def score_bad(self, in_points):
        self.score -= (in_points * self.bad_multi)
        if self.score < 0: self.score = 0

    def score_good(self, in_points):
        self.score += in_points

    def post_process(self, in_mat, in_motion_mat):
        if self.prestart_time >= 0:
            result = draw_str(in_mat, (self.prestart_time_x, self.prestart_time_y),
                    'Game starts in: %0d' % self.prestart_time)

        else:
            result = draw_str(in_mat, (self.time_x, self.time_y),
                    'Time left: %0d' % self.time_left)

            result = draw_str(in_mat, ((IMG_WIDTH/2)-30,IMG_HEIGHT-10), 
                    'Score: %0d' % self.score)
    

class MessBubbles(object):
    def __init__(self, in_x, in_y):
        self.enabled = True

        class doneObj(QObject):
            done_animation = pyqtSignal(int, int, 'QString')
        self.done_sig = doneObj()

        build_item = Bubble()
        build_item.x = in_x
        build_item.y = in_y

        self.max_mess_bubbles = 50
        self.game_popped_increment = 5
        self.game_popped_radius = 5
        self.game_popped_bubbles = []

        self.add_popped_bubbles(build_item)

    def add_popped_bubbles(self, in_item):
        for i in range(self.max_mess_bubbles):
            xr = (IMG_WIDTH/8)
            if i > xr:
                new_x = in_item.x + (random.randrange(1, xr, 1))
            else:
                new_x = in_item.x - (random.randrange(1, xr, 1))
                #new_y = in_item.y - (random.randrange(10, 20, 1))

            yr = 5 
            new_y = in_item.y + (random.randrange(1, yr, 1))
            nb = Bubble(increment=self.game_popped_increment, 
                        radius=self.game_popped_radius,
                        color=(0,255,0),
                        start_x = new_x, start_y = new_y)
            #self.log.info("Popped: " + str(nb.x))
            self.game_popped_bubbles.append(nb)

    def game_process(self, in_mat, in_motion_mat):
        at_least_one = False
        overlay = in_mat.copy()

        for item in self.game_popped_bubbles:
            # If bubble has moved to the top of the screen starting
            # area, consider the animation done, and don't draw it
            if item.y >= 0:
                
                result = item.local_pop_check(in_motion_mat)
                item.auto_fade()

                cv2.circle(overlay, (item.x, item.y), item.radius, item.color,
                        thickness=-1, lineType=cv2.CV_AA)

                at_least_one = True
                if not result:
                    item.animate()

        # From:
        # http://bistr-o-mathik.org/2012/06/13/simple-transparency-in-opencv/
        opacity = item.opacity
        cv2.addWeighted( overlay, opacity, in_mat, 1-opacity, 0, in_mat)

        # If not a single bubble left, set enabled to false to remove it from
        # the processing queue
        if not at_least_one:
            self.enabled = False
            self.done_sig.done_animation.emit(item.x, item.y, "mess done")


class GroupBubbles(object):
    def __init__(self, count=10):
        logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
            level=logging.DEBUG)
        self.log = logging.getLogger()
        self.enabled = True

        class popObj(QObject):
            popped = pyqtSignal(int, int, 'QString')
        self.pop_sig = popObj()
        
        self.count = count
        self.bubbles = []
        for i in range(self.count):
            self.bubbles.append(  Bubble() )


    def game_process(self, in_mat, in_motion_mat):
        for item in self.bubbles:
            result = item.local_pop_check(in_motion_mat)
            if result:
                self.pop_sig.popped.emit(item.x, item.y, "popped")
                item.reset_position()

            else:
                item.animate()
                cv2.circle(in_mat, (item.x, item.y), item.radius, item.color,
                        thickness=-1, lineType=cv2.CV_AA)


class Bubble(object):
    def __init__(self, color=(255,0,0), radius=20, increment=8, start_x=0,
                    start_y=0):
        self.max_x = IMG_WIDTH
        self.max_y = IMG_HEIGHT
        self.x = start_x
        if start_x == 0:
            self.x = random.randrange(0, self.max_x, 1)
        self.y = start_y
        if start_y == 0:
            self.y = -10 - random.randrange(100, self.max_y, 1)
        self.radius = radius
    
        self.color = color
        self.increment = increment
        self.points = 10

        self.fade_increment = 5
        self.opacity = 1
        self.opacity_increment = 0.01

        class popObj(QObject):
            popped = pyqtSignal(int, int, 'QString')
        self.pop_sig = popObj()

    def animate(self):
        self.y += self.increment
        # Add the radius distance to make sure huge bubbles animate all the way
        # off screen
        if self.y > (self.max_y + self.radius):
            self.y = -10 - random.randrange(100, self.max_y, 1)
            self.x = random.randrange(0, self.max_x, 1)
            #self.x = 160

    # Gradually fade the bubble out so it is no longer visible
    # if it's transparent, move it off the screen so the popped bubble animation
    # resets
    def auto_remove(self):
        red = self.color[1] - self.fade_increment
        if red < 0:
            self.y = -10
        self.color = (0, red, 0)

    def auto_fade(self):
        self.opacity = self.opacity - self.opacity_increment
        if self.opacity < 0:
            self.y = -10

    def reset_position(self):
        self.y = -10 - random.randrange(100, self.max_y, 1)
        self.x = random.randrange(0, self.max_x, 1)

    def game_process(self, in_mat):
        self.animate()
        cv2.circle(in_mat, (self.x, self.y), self.radius, self.color,
                   thickness=-1, lineType=cv2.CV_AA)

    def local_pop_check(self, motion_blob_mat):
        if self.y <= 0 or self.y >= IMG_HEIGHT : return 0
        if self.x <= 0 or self.x >= IMG_WIDTH : return 0
       
        # Is there motion precisely where the bubble is?
        mot_threshold = 1
        if motion_blob_mat.item(self.y, self.x) > mot_threshold:
            return 1
        return 0


class RoughTest(Bubble):
    ''' 
    Constantly in flux place holder for trying different effects.
    '''
    def __init__(self, in_ref_mat, in_radius=10, duration=10):
        Bubble.__init__(self, color=(128,255,128), radius=in_radius)
        logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
            level=logging.DEBUG)
        self.log = logging.getLogger()
        self.enabled = True
        self.preproc_enabled = True

        self.input_ref = in_ref_mat


    def pre_process(self, in_mat, in_motion_mat):
        # Experiments based on the blogspot below to skeletonize the motion blob

        #self.in_test = in_motion_mat
        self.log.info("rough preproc")
        size = IMG_HEIGHT, IMG_WIDTH, 3
        black_fr = numpy.zeros(size, dtype=numpy.uint8)
        #cv2.bitwise_not(self.input_ref, in_motion_mat)
        cv2.rectangle(self.input_ref,
                         (100, 100), 
                         (400, 400),
                         (255,255,255), thickness=5, lineType=cv2.CV_AA)
        
        ret_mat = self.input_ref
        return ret_mat, black_fr


class SkeletonBubble(Bubble):
    def __init__(self, in_ref_mat, in_radius=10, duration=10):
        Bubble.__init__(self, color=(128,255,128), radius=in_radius)
        self.enabled = True
        self.preproc_enabled = True

        self.pass_count_threshold = 100


    def pre_process(self, in_mat, in_motion_mat):
        '''
        Based on: http://opencvpython.blogspot.com/2012/05/\
                skeletonization-using-opencv-python.html
        Provide a primitive skeletonization effect of the motion blob previously
        detected. Take the motion blob, convert it back to full color, then run
        that through the skeletonization procedure and display that over the
        recorded background image.
        '''

        new_color = cv2.cvtColor(in_motion_mat, cv2.COLOR_GRAY2BGR)
        img = cv2.cvtColor(new_color, cv2.COLOR_BGR2GRAY)

        #img = in_motion_mat
        size = numpy.size(img)
        skel = numpy.zeros(img.shape,numpy.uint8)
       
        ret,img = cv2.threshold(img,127,255,0)
        element = cv2.getStructuringElement(cv2.MORPH_CROSS,(3,3))
        done = False
      
        pass_count = 0
        while( not done):
            eroded = cv2.erode(img,element)
            temp = cv2.dilate(eroded,element)
            temp = cv2.subtract(img,temp)
            skel = cv2.bitwise_or(skel,temp)
            img = eroded.copy()
        
            pass_count += 1
            if pass_count > self.pass_count_threshold:
                #print "force exit", pass_count
                return skel, skel


            zeros = size - cv2.countNonZero(img)

            if zeros==size:
                done = True
                #print "pass count ", pass_count

        #print "end of the line exit", pass_count
        return skel, skel




    def game_process(self, in_mat, in_motion_mat):
        if self.preproc_enabled: return

        result = self.local_pop_check(in_motion_mat)
        if result:
            self.pop_sig.popped.emit(self.x, self.y, "popped")
            self.reset_position()

        else:
            self.animate()
            cv2.rectangle(in_mat,
                         (self.x, self.y), 
                         (self.x + self.radius, self.y + self.radius), 
                         self.color, thickness=-1, lineType=cv2.CV_AA)



class FireBubble(Bubble):
    def __init__(self, in_ref_mat, in_radius=10, duration=10):
        Bubble.__init__(self, color=(128,255,128), radius=in_radius)
        self.enabled = True
        self.preproc_enabled = True

        self.fire_ref_color = in_ref_mat


    # Draw the contours around the motion blob, animate color fire coming out
    def pre_process(self, in_mat, in_motion_mat):

        conts, hier = cv2.findContours( in_motion_mat, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = [cv2.approxPolyDP(cnt, 3, True) for cnt in conts]

        levels = 3
        cv2.drawContours(in_mat, contours, (-1,3)[levels <= 0], (128,255,255),
                3, cv2.CV_AA, hier, abs(levels) )


    def game_process(self, in_mat, in_motion_mat):
        if self.preproc_enabled: return

        result = self.local_pop_check(in_motion_mat)
        if result:
            self.pop_sig.popped.emit(self.x, self.y, "popped")
            self.reset_position()

        else:
            self.animate()
            cv2.rectangle(in_mat,
                         (self.x, self.y), 
                         (self.x + self.radius, self.y + self.radius), 
                         self.color, thickness=-1, lineType=cv2.CV_AA)

            
class SmoosherBubble(Bubble):
    '''
    When the actor collides with the smoosher bubble ( a green square ), the pre
    processor will be updated with a gradually shrunken version of the motion
    blob, which is in turn used to extract the actor boundaries. This mask is
    then used on the main camera image to present a full version of the actor
    over the reference image for a 'you shrunk me!' mode. Timers execute an
    animated restoration to normal size.
    '''
    def __init__(self, in_ref_mat, in_radius=20, duration=10):
        Bubble.__init__(self, color=(0,255,0), radius=in_radius )
        self.enabled = True
        self.preproc_enabled = False

        self.smoosh_ref_color = in_ref_mat
        self.min_down_scale = 0.25
        self.down_scale_increment = 0.025
        self.up_scale_increment = 0.10
        self.scale_factor = 1
        self.scale_mode = 1


    def pre_process(self, in_mat, in_motion_mat):
        # Create an all black background image with the shrunken
        # motion area on top of it
        back_col = cv2.cvtColor(in_motion_mat, cv2.COLOR_GRAY2BGR)
        mask_res = cv2.bitwise_and(in_mat, back_col)

        ds = self.scale_factor
        down_res = cv2.resize(mask_res, (0,0), fx=ds, fy=ds) 

        # Define the place for the shrunken result on the new image. Put it in
        # the center lower middle so it looks like you're in the scene
        y_top = IMG_HEIGHT - down_res.shape[0]
        y_bot = y_top + down_res.shape[0] 
        x_lef = (IMG_WIDTH - down_res.shape[1])/2
        x_rig = x_lef + down_res.shape[1]

        # Broadcast the new mask into an all black (color) image
        size = IMG_HEIGHT, IMG_WIDTH, 3
        black_fr = numpy.zeros(size, dtype=numpy.uint8)

        # Rough and ready y axis shift of shrink so it's not behind the text
        y_offset = 0
        y_diff = y_bot - y_top
        if y_diff < 200:
            y_offset = 20
        y_top -= y_offset
        y_bot -= y_offset
        black_fr[y_top:y_bot, x_lef:x_rig] = down_res

        # Convert to gray, use to create an inverse mask of the
        # reference.
        newm_res = cv2.cvtColor(black_fr, cv2.COLOR_BGR2GRAY)

        ret, nthr_res = cv2.threshold(newm_res, 1, 255,
                cv2.THRESH_BINARY)
        nthr_res = cv2.bitwise_not(nthr_res)
        retc_res = cv2.cvtColor(nthr_res, cv2.COLOR_GRAY2BGR)
        back_res = cv2.bitwise_and(self.smoosh_ref_color, retc_res)

        # Now bitwise and them together to preserve the color
        # information
        cv2.bitwise_or(back_res, black_fr, in_mat)

        # Now take the shrunken down motion mask and set it as the input image
        # for better collision detection, flip the inverse back 
        cv2.bitwise_not(nthr_res, in_motion_mat)

        self.animate_pre_process()
        return in_mat, in_motion_mat

    def animate_pre_process(self):
        # Increment the down scale to show the shrinking effect

        # Mode 1 is shrink
        if self.scale_mode:
            self.scale_factor -= self.down_scale_increment
            if self.scale_factor <= self.min_down_scale:
                self.scale_factor = self.min_down_scale
                QTimer.singleShot(3000, self.toggle_mode)
        else:
            self.scale_factor += self.up_scale_increment
            if self.scale_factor >= 1:
                self.scale_factor = 1

    def toggle_mode(self):
        self.scale_mode = 0 

    def game_process(self, in_mat, in_motion_mat):
        if self.preproc_enabled: return
        self.scale_mode = 1 # Make sure the shrink animation is restored

        result = self.local_pop_check(in_motion_mat)
        if result:
            self.pop_sig.popped.emit(self.x, self.y, "popped")
            self.down_scale = 1
            self.reset_position()

        else:
            self.animate()
            cv2.rectangle(in_mat,
                         (self.x, self.y), 
                         (self.x + self.radius, self.y + self.radius), 
                         self.color, thickness=-1, lineType=cv2.CV_AA)


class UpBubble(Bubble):
    '''
    Animate a circle that goes up from the popped bubble location for a simple
    pop feedback effect.
    '''
    def __init__(self, in_x, in_y, in_radius):
        Bubble.__init__(self, color=(255,0,0))
        self.enabled = True
        self.x = in_x
        self.y = in_y
        self.radius = in_radius
        self.radius_increment = 1
        self.animate_distance = self.y - 75

    def animate(self):
        self.y -= self.increment
        self.radius -=  self.radius_increment
        if self.radius < 1: self.radius = 1
        # Add the radius distance to make sure huge bubbles animate all the way
        # off screen
        if self.y <  self.animate_distance:
            self.enabled = False

    def game_process(self, in_mat, in_motion_mat):
        self.animate()
        cv2.circle(in_mat, (self.x, self.y), int(self.radius), self.color,
                    thickness=1, lineType=cv2.CV_AA)



class BadBubble(Bubble):
    '''
    The red bubble that pops the green mess all over the player, as well as
    decreases the score.
    '''
    def __init__(self, in_radius=20):
        Bubble.__init__(self, color=(0,0,255), radius=in_radius)
        self.enabled = True

    def harder(self, in_chg):
        # Make the bubble bigger
        self.radius += in_chg

    def game_process(self, in_mat, in_motion_mat):
        result = self.local_pop_check(in_motion_mat)
        if result:
            self.pop_sig.popped.emit(self.x, self.y, "popped")
            self.reset_position()

        else:
            self.animate()
            cv2.circle(in_mat, (self.x, self.y), self.radius, self.color,
                        thickness=-1, lineType=cv2.CV_AA)


    def local_pop_check(self, motion_blob_mat):
        '''
        Expand the collision boundary detection to cover more than just the
        center of the bubble (default). Proscribe an internal square boundary
        box that covers a large portion of the 'collision area' within the
        circle. This is important as the circle can become huge. 
        '''

        if self.y <= 0 or self.y >= IMG_HEIGHT : return 0
        if self.x <= 0 or self.x >= IMG_WIDTH : return 0
       
        # Check square edge that is sure to be in the radius
        mot_threshold = 1
        radius_margin = self.radius / 4
        start_x = self.x - (self.radius - radius_margin)
        end_x   = self.x + (self.radius - radius_margin)
        start_y = self.y - (self.radius - radius_margin)
        end_y   = self.y + (self.radius - radius_margin)
        if start_y < 0: start_y = 0
        if start_x < 0: start_x = 0
        if end_y > IMG_HEIGHT: end_y = IMG_HEIGHT
        if end_x > IMG_WIDTH : end_x = IMG_WIDTH

        y_jump = 1
        x_jump = 1

        curr_y = start_y
        try:
            while curr_y < end_y:
                curr_x = start_x
                while curr_x < end_x:
                    if motion_blob_mat.item(curr_y, curr_x) > mot_threshold:
                        return 1
                    curr_x += x_jump

                curr_y += y_jump
        except IndexError:
            # Assume it's at an edge, so ignore it
            pass

        return 0


class MainBubbler(QObject):
    def __init__(self):
        super(MainBubbler, self).__init__()

        logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
            level=logging.DEBUG)
        self.log = logging.getLogger()

        self.setup_video_and_windows()
        self.setup_queues()

        self.rm = ReferenceMAT()
        self.di = DebugInfo()

        # Force initial processing 
        self.rm.pre_process(self.current_frame, self.current_frame)
        self.post_queue.put(self.di)

        # Wait for the camera to stabilize, then set the reference
        self.ref_timer = QTimer(self)
        self.ref_timer.timeout.connect(self.new_reference)
        self.ref_timer.setSingleShot(True)
        if DEBUG or VIDEO_ONLY:
            self.ref_timer.start(90)
        else:
            self.ref_timer.start(1900)

        # Create the game object which auto-countdown starts after 3 seconds
        if DEBUG:
            if not VIDEO_ONLY:
                QTimer.singleShot(100, self.create_game)
        else:
            if not VIDEO_ONLY:
                QTimer.singleShot(2000, self.create_game)

        # Start the main event timer
        self.queue_timer = QTimer(self)
        self.queue_timer.timeout.connect(self.process_queues)
        self.queue_timer.setSingleShot(True)
        self.queue_timer.start(0)

    def setup_video_and_windows(self):
        cap_str = "1:size=" + str(IMG_WIDTH) + "x" + str(IMG_HEIGHT)
        self.cam = video.create_capture( cap_str )

        # TODO: can you get speed by flipping in logitech? What if you flip the
        # H.264 stream?
        ret, img = self.cam.read()
        self.current_frame = cv2.flip(img, 1)

        cv2.namedWindow("Processed", cv2.CV_WINDOW_AUTOSIZE )
        cv2.moveWindow("Processed",0,0)

        cv2.namedWindow("Live", cv2.WINDOW_OPENGL)
        cv2.moveWindow("Live",800,0)

    def create_game(self):
        self.gc = GameControl()
        self.gc.game_sig.start_game.connect(self.on_start_game)
        self.gc.game_sig.stop_game.connect(self.on_stop_game)
        self.post_queue.put(self.gc)


    def on_start_game(self):
        self.log.info("Start game")
        tg = GroupBubbles()
        tg.pop_sig.popped.connect(self.on_good_pop)
        self.game_queue.put( tg )

        self.bb = BadBubble( self.gc.bad_radius )
        self.bb.pop_sig.popped.connect(self.on_bad_pop)
        self.game_queue.put( self.bb )
    
        self.add_smoosher_timer = QTimer()
        self.add_smoosher_timer.setSingleShot(True)
        self.add_smoosher_timer.timeout.connect(self.add_smoosher)
        if DEBUG:
            self.add_smoosher_timer.start(1000)
        else:
            self.add_smoosher_timer.start(3000)

    def on_stop_game(self):
        self.log.info("Stop game")
        # temporarily stop the queue
        self.queue_timer.stop()

        # dequeue all the objects
        while True:
            try:
                item = self.game_queue.get_nowait()
            except Queue.Empty:
                break
            except:
                self.log.critical("Clear GAMEPROCQ: " + str(sys.exc_info()))
                break

        # Restart the queue
        self.queue_timer.start(1)

    def setup_queues(self):
        self.pre_queue = Queue.Queue()
        self.post_queue = Queue.Queue()
        self.game_queue = Queue.Queue()

    def closeEvent(self):
        cv2.destroyAllWindows()
        self.queue_timer.stop()

    def on_good_pop(self, in_x, in_y):
        #self.log.info("on good pop " + str(in_x) + " " + str(in_y))
        self.game_queue.put( UpBubble(in_x, in_y, self.gc.good_radius) )
        self.gc.score_good( 10 )

    def on_bad_pop(self, in_x, in_y):
        self.log.info("on bad pop " + str(in_x) + " " + str(in_y))
        self.gc.score_bad( 10 )

        # Stop the bad bubble, increase it's size for next pass
        self.bb.enabled = False
        self.bb.harder( self.gc.bad_radius_jump)

        mg = MessBubbles(in_x, in_y)
        mg.done_sig.done_animation.connect(self.mess_done)
        self.game_queue.put( mg )

    def mess_done(self, in_x, in_y):
        self.log.info("reenable bad bubble")
        self.bb.enabled = True
        self.game_queue.put( self.bb )

    def new_reference(self):
        self.pre_queue.put( self.rm )

    def add_chopper(self):
        self.log.info("add chopper")

    def add_smoosher(self):
        self.log.info("add smoosher")
        self.sb = SmoosherBubble( self.rm.reference_color,
                duration=self.gc.show_smoosh_duration)
        self.sb.pop_sig.popped.connect(self.on_smoosher_pop)
        self.game_queue.put( self.sb )

    def add_fire(self):
        self.log.info("Add fire ")
        self.fb = FireBubble(self.rm.reference_color)
        self.pre_queue.put( self.fb )

    def add_skeleton(self):
        self.log.info("skeleton")
        self.skb = SkeletonBubble(self.rm.reference_color)
        self.pre_queue.put( self.skb )

    def on_smoosher_pop(self):
        self.log.info("on smoosher pop")
        self.sb.preproc_enabled = True
        self.pre_queue.put( self.sb )
        QTimer.singleShot(6000, self.reset_smoosher_start)

    def reset_smoosher_start(self):
        self.log.info("Reset smoosher")
        self.sb.preproc_enabled = False

    def find_motion(self, in_frame):
        self.primary_kernel_size = 20
        self.primary_threshold_level = 20

        reference_gray = self.rm.reference_gray

        gray_frame = cv2.cvtColor(in_frame, cv2.COLOR_BGR2GRAY)
        diff_frame = cv2.absdiff(reference_gray, gray_frame)

        kernel_size = self.primary_kernel_size
        blur_frame = cv2.blur(diff_frame, (kernel_size, kernel_size))

        threshold_level = self.primary_threshold_level
        ret, thre_frame = cv2.threshold( blur_frame, threshold_level, 255,
                        cv2.THRESH_BINARY)

        return thre_frame

    def process_queues(self):
        # Every N msec, process the three queues:
        # pre-process: take new reference, shrink motion image and change
        # collision frame (if desired), etc.
        # game progress: do collision detection, move actors
        # post process: render all items, display to screen, based on what
        # happened in game progress, add new acquisition parameters to pre
        # process queue as well as rendering changes to post process and
        # different rules to game progress queue

        # First, get the current frame from the camera
        ret, self.img = self.cam.read()
        self.current_frame = cv2.flip(self.img, 1)

        # This should probably be moved to a pre processing object
        self.motion_blob = self.find_motion(self.current_frame)

        self.pre_process()
        self.game_process()
        self.post_process()

        self.display_image()
        self.queue_timer.start(1)

    def pre_process(self):
        post_list = []
        while True:
            try:
                item = self.pre_queue.get_nowait()
                #self.log.info("Preproc " + str(item))
                cf, mb = item.pre_process(self.current_frame, self.motion_blob)
                self.current_frame, self.motion_blob = cf, mb
                post_list.append(item)

            except Queue.Empty:
                break

            except:
                self.log.critical("PREPROCQ: " + str(sys.exc_info()))
                break

        for preproc_item in post_list:
            if preproc_item.preproc_enabled:
                #self.log.info("Re-add " + str(preproc_item))
                self.pre_queue.put(preproc_item)



    def game_process(self):
        post_list = []
        while True:
            try:
                item = self.game_queue.get_nowait()
                #self.log.info("GAMEQ" + str(item))
                item.game_process(self.current_frame, self.motion_blob)
                post_list.append(item)

            except Queue.Empty:
                #self.log.info("game empty" + str(sys.exc_info()))
                break

            except:
                self.log.critical("GAMEQ: " + str(sys.exc_info()))
                self.log.critical(str(sys.exc_traceback.tb_lineno ))
                
                break

        # Check if items are still enabled, put them back on the queue for the
        # next pass
        # TODO: do these items get destroyed automatically?
        for game_item in post_list:
            if game_item.enabled:
                #self.log.info("Re-add " + str(game_item))
                self.game_queue.put(game_item)
    


    def post_process(self):
        post_list = []
        while True:
            try:
                item = self.post_queue.get_nowait()
                #self.log.info("POSTPROCQ" + str(item))
                item.post_process(self.current_frame, self.motion_blob)
                post_list.append(item)

            except Queue.Empty:
                #self.log.info("post empty" + str(sys.exc_info()))
                break

            except:
                self.log.critical("POSTPROCQ: " + str(sys.exc_info()))
                break

        # Put this back on the queue for processing next pass
        for effect in post_list:
            if effect.enabled:
                self.post_queue.put(effect)

    def display_image(self):
        cv2.imshow("Processed", self.motion_blob)
        cv2.imshow("Live", self.current_frame)
        self.update_interface()

    def update_interface(self):
        ch = 0xFF & cv2.waitKey(1) 
        if   ch == 27 or ch == ord('q'):
            self.closeEvent()

        elif ch == ord('c'):
            self.add_chopper()

        elif ch == ord('s'):
            self.add_smoosher()
        
        elif ch == ord('1'):
            self.add_fire()
        
        elif ch == ord('2'):
            self.add_skeleton()

        elif ch == ord('u'):
            nv = self.skb.pass_count_threshold + 1
            self.log.info("Skeleton pass count threshold to " + str(nv))
            self.skb.pass_count_threshold = nv

        elif ch == ord('d'):
            nv = self.skb.pass_count_threshold - 1
            self.log.info("Skeleton pass count threshold to " + str(nv))
            self.skb.pass_count_threshold = nv

        elif ch == ord('3'):
            self.log.info("rough test")
            self.roughb = RoughTest(self.rm.reference_color)
            self.pre_queue.put( self.roughb)

        elif ch == ord('r'):
            self.new_reference()

        elif ch == ord('f'):
            self.di.enabled = not self.di.enabled
            self.post_queue.put(self.di)
       
        elif ch == ord('n'):
            try:
                self.gc.reset_game()
                self.gc.game_sig.stop_game.emit()
            except:
                self.log.warn("New game: " + str(sys.exc_info()))


if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option("--debug", action="store_true", dest="DEBUG")
    parser.add_option("--video-only", action="store_true", dest="VIDEO_ONLY")
    (options,args) = parser.parse_args()
    DEBUG = options.DEBUG
    VIDEO_ONLY = options.VIDEO_ONLY

    app = QApplication(sys.argv)
    mb = MainBubbler()
    sys.exit(app.exec_())
