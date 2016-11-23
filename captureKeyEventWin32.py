import pythoncom, pyHook
import thread
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

current_milli_time = lambda: int(round(time.time() * 1000))

def OnKeyboardEvent(event):
    global stop, left_num, right_num, brk_num, acc_num
    print 'MessageName:',event.MessageName
    #print 'Message:',event.Message
    print 'Time:',current_milli_time()
    #print 'Window:',event.Window
    #print 'WindowName:',event.WindowName
    #print 'Ascii:', event.Ascii, chr(event.Ascii)
    print 'Key:', event.Key
    print 'KeyID:', event.KeyID
    #print 'ScanCode:', event.ScanCode
    #print 'Extended:', event.Extended
    #print 'Injected:', event.Injected
    #print 'Alt', event.Alt
    #print 'Transition', event.Transition
    print '---'

    if event.KeyID == 27: #ESC to leave
        stop = True
        f.close()
        return True

    if event.KeyID in (37, 38, 39, 40):
        if event.MessageName == 'key down':
            if event.KeyID == 37: # left
                left_num += 1
                label='-1'
            elif event.KeyID == 39: # right
                right_num += 1
                label='1'
            elif event.KeyID == 40: # break
                brk_num += 1
                label='b'
            elif event.KeyID == 38: # acc
                acc_num += 1
                label='0'

            f.write(str(current_milli_time()) + ':' + label + '\n')
            # put the key into queue
        else:
            # Key Up
            dtime = current_milli_time()
            stime = 0
            label = '0'
            if event.KeyID == 37:
                stime = leftQ.get()
                dtime = 0 - (dtime - stime) / 1000
            elif event.KeyID == 39:
                stime = rightQ.get()
                dtime = (dtime - stime) / 1000

            if dtime > 1.5:
                label = '3'
            elif 0.75 < dtime <= 1.5:
                label = '2'
            elif 0 < dtime <= 0.75:
                label = '1'
            elif dtime < -1.5:
                label = '-3'
            elif -1.5 <= dtime < -0.75:
                label = '-2'
            elif -0.75 <= dtime < 0:
                label = '-1'
            else:
                label = '0'
            f.write(str(stime) + ':' + label + '\n')
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
                    cv2.imwrite("n/"+str(frame_ts)+'.png', frame)
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