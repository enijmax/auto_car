import pythoncom, pyHook
import thread, threading
import datetime, time
import Queue
import shutil
import sys, math
import cv2
from os import path, listdir, walk, makedirs, remove

# global variables
stop = False
left_num = 0
right_num = 0
acc_num = 0
brk_num = 0
key_file = time.strftime('%Y-%m-%d_%H-%M-%S.txt')
lock = threading.Lock()
g_pkeyb = 0

KC_LEFT = 37
KC_UP = 38
KC_RIGHT = 39
KC_DN = 40

TAG_ACC_LEFT = "ACC_LEFT"
TAG_ACC_RIGHT = "ACC_RIGHT"
TAG_BRK_LEFT = "BRK_LEFT"
TAG_BRK_RIGHT = "BRK_RIGHT"
TAG_ACC = "ACC"
TAG_BRK = "BRK"
TAG_LEFT = "LEFT"
TAG_RIGHT = "RIGHT"

B_ACC_LEFT = 10
B_ACC_RIGHT = 9
B_ACC = 8
B_BRK_LEFT = 6
B_BRK_RIGHT = 5
B_BRK = 4
B_LEFT = 2
B_RIGHT = 1

current_milli_time = lambda: int(round(time.time() * 1000))

def ConvKeyIDToBit(pkey):
    if (pkey == KC_LEFT):
        return B_LEFT
    elif (pkey == KC_RIGHT):
        return B_RIGHT
    elif (pkey == KC_UP):
        return B_ACC
    elif (pkey == KC_DN):
        return B_BRK

# If key pressed , release it, if not pressed, pressed it.
def SetKeyStatueSwitch(pkey):
    global g_pkeyb
    bkey = ConvKeyIDToBit(pkey)
    if (bkey in (B_ACC, B_BRK, B_LEFT, B_RIGHT)):
        with lock:
            g_pkeyb = g_pkeyb ^ bkey
        return True
    return False

def OnKeyboardEvent(event):
    global stop, left_num, right_num, brk_num, acc_num
    label = "N"

    if event.KeyID == 27: #ESC to leave
        stop = True
        f.close()
        return True

    if event.KeyID in (KC_LEFT, KC_RIGHT, KC_UP, KC_DN):
        print 'MessageName:',event.MessageName
        print 'Time:',current_milli_time()
        print 'Key:', event.Key
        print 'KeyID:', event.KeyID
        print '---'

        if (SetKeyStatueSwitch(event.KeyID) == False):
            print 'Not expected KEY:', event.KeyID
        # get key flags
        if (g_pkeyb & B_ACC_RIGHT) == B_ACC_RIGHT:
            right_num += 1
            label = TAG_ACC_RIGHT
        elif (g_pkeyb & B_ACC_LEFT) == B_ACC_LEFT:
            left_num += 1
            label = TAG_ACC_LEFT
        elif (g_pkeyb & B_BRK_RIGHT) == B_BRK_RIGHT:
            right_num += 1
            label = TAG_BRK_RIGHT
        elif (g_pkeyb & B_BRK_LEFT) == B_BRK_LEFT:
            left_num += 1
            label = TAG_BRK_LEFT
        elif (g_pkeyb & B_ACC) == B_ACC: # Acc
            acc_num += 1
            label = TAG_ACC
        elif (g_pkeyb & B_BRK) == B_BRK: # Brake
            brk_num += 1
            label = TAG_BRK
        elif (g_pkeyb & B_LEFT) == B_LEFT: # Left
            left_num += 1
            label = TAG_LEFT
        elif (g_pkeyb & B_RIGHT) == B_RIGHT: # Right
            right_num += 1
            label = TAG_RIGHT

        f.write(str(current_milli_time()) + ':' + label + '\n')

    # return True to pass the event to other handlers
    return True

def moveAllVdoFiles(folder):
    for vdofile in listdir(folder):
        if vdofile.endswith('.mp4'):
            print 'Moving '+folder + '\\' + vdofile
            shutil.move(folder+'\\'+vdofile, "./"+vdofile)

# return time stamp from filename YYYY-mm-dd_HH-MM-SS
def getTimeStampFromFileName(fileName):
    return int(time.mktime(datetime.datetime.strptime(path.splitext(fileName)[0], "%Y-%m-%d_%H-%M-%S").timetuple()) * 1000)

# find closest filename.
def findNearByVideo(ts, folder="."):
    closest_vdo_filename = ''
    closest_vts = 0
    smallest_delta = -1
    for vdofile in listdir(folder):
        if vdofile.endswith('.mp4'):
            #print vdofile
            vts = getTimeStampFromFileName(vdofile)
            delta = math.fabs(vts - ts)
            if smallest_delta == -1:
                smallest_delta = delta
                closest_vdo_filename = vdofile
                closest_vts = vts
            elif smallest_delta > delta:
                smallest_delta = delta
                closest_vdo_filename = vdofile
                closest_vts = vts
    return [closest_vdo_filename, closest_vts]

def labelingFrames(k_f, v_f):
    global key_file

    neture_num = 0
    left_num = 0
    right_num = 0
    brk_num = 0
    acc_num = 0

    # read video 
    vidcap = cv2.VideoCapture(v_f)
    frame_ts = vdo_ts
    curr_frame_ts = vdo_ts

    # read key mapping file
    key_content = open(k_f, 'rb').readlines()
    fetchKey = True
    fetchFrame = True
    for line in key_content:
        n_line = line.strip()   # remove unnecessary characters
        ts = n_line.split(':')
        # create folders
        if path.isdir("n") == False:
            makedirs("n")
        if path.isdir(ts[1]) == False:
            makedirs(ts[1])

        # video frame before the key event more then 33 ms, check the next frame
        # 30 fps
        delta_t = frame_ts - long(ts[0])
        frame = None
        while delta_t < -33:
            frame_ts += (1000/30)
            if frame_ts - curr_frame_ts > 500: # 500ms to capture one screen
                if frame is not None:
                    print "class: n - " + str(frame_ts)
                    cv2.imwrite("n/"+str(frame_ts)+'.png', frame)   # save the frame as n-class if user didn't press anykey
                    neture_num += 1
                    frame = None
                curr_frame_ts = frame_ts

            flag, frame = vidcap.read()
            if flag:
                cv2.imshow('video', frame)
                delta_t = frame_ts - long(ts[0])
            else:
                break

            # Press esc to quit the program
            if cv2.waitKey(1) == 27:
                break

        # Find the relative frame in 20ms
        if -33 <= delta_t <= 33 and frame is not None:
            # this is the right frame, save it to the ts[1] folder
            print "class: "+ts[1] + ' - ' +ts[0]
            cv2.imshow('video', frame)
            cv2.imwrite(ts[1]+'/'+str(frame_ts)+'.png', frame)
            if ts[1] == '-1':
                left_num += 1
            elif ts[1] == '1':
                right_num += 1
            elif ts[1] == 'b':
                brk_num += 1
            elif ts[1] == '0':
                acc_num += 1
            elif ts[1] == 'n':
                neture_num += 1

        # Press esc to quit the program
        if cv2.waitKey(1) == 27:
            break

    print "================Summary==================\nLeft:"+str(left_num)+"\nNeture:"+str(neture_num)+"\nAcc:"+str(acc_num)+"\nRight:"+str(right_num)+"\nBreak:"+str(brk_num)
    vidcap.release()
    cv2.destroyAllWindows()
    return


### Main start here ###
# Prepare  file
f = open(key_file, 'wb')
# create a hook manager
hm = pyHook.HookManager()
# watch for all mouse events
hm.KeyDown = OnKeyboardEvent
#hm.KeyUp = OnKeyboardEvent
# set the hook
hm.HookKeyboard()
# wait forever
while stop == False:
    pythoncom.PumpWaitingMessages()
print "Acc = ", acc_num
print "Left = ", left_num
print "Right = ", right_num
print "Break = ", brk_num
f.close()
print "Waiting 3 sec for video file saved."
hm.UnhookKeyboard()
hm.KeyDown = None
# Move video file to current location
time.sleep(3)
moveAllVdoFiles("C:\\Users\\Rider\\Videos\\")

# find the matched video filename in the same folder
timestamp = getTimeStampFromFileName(key_file)
print 'filetimestamp=', timestamp
vdo_file, vdo_ts = findNearByVideo(timestamp)
print 'matched vdo filename=', vdo_file
if vdo_ts == 0:
    print 'No matched video file'
    remove(key_file)
    exit()

# Ask user really need to mapping the key events?
ret = raw_input('Do you really want to convert it?(Yes/No)')
if ret == 'Yes' or ret == 'Y' or ret == 'y' or ret == 'yes':
    # cliping the video into frame with label.
    labelingFrames(key_file, vdo_file)
else:
    print "Delete the key mapping & vdo"
    remove(key_file)
    remove(vdo_file)

print "END"