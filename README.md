# BubblerHope
Use a webcam, opencv, and drawing primitives to provide a simple game with real time visual effects.

The Bubbler - be memorable. 
---------------------------

Demonstration video:
        http://nathanharrington.info/files/bubbler_long_demo.mp4

Requirements:
        Python (x,y) 2.7.5.1 with PyOpenCv 
        usb webcam

Developed on:
        Windows 8/8.1/7
        Lenovo IdeaPad U430 Intel core i5-4200U 1.6Ghz 4GB RAM
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

