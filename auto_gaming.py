import pythoncom, pyHook
import win32gui, win32ui, win32con, win32api
import pyscreenshot as ImageGrab
from PIL import Image
#from multiprocessing import Process, freeze_support
import thread
import time
import caffe
import numpy as np
from caffe.proto import caffe_pb2
from google.protobuf import text_format
import scipy.misc

x = 0
y = 0
w = 640
h = 480

target_hwnd = None
stop = False
label = None
left_num = 0
right_num = 0
up_num = 0

FOLDER = "20161116_2_28.0"
DEPLOY_FILE = "..\\models\\game_models\\"+FOLDER+"\\deploy.prototxt"
CAFFE_MODE_FILE = "..\\models\\game_models\\"+FOLDER+"\\snapshot_iter_308.caffemodel"
MEAN_FILE = "..\\models\\game_models\\"+FOLDER+"\\mean.binaryproto"

current_milli_time = lambda: int(round(time.time() * 1000))

def enumHandler(hwnd, lParam):
	global x, y, w, h, target_hwnd
	if win32gui.IsWindowVisible(hwnd):
		#print "Window Text:", win32gui.GetWindowText(hwnd)
		if 'Speed Dreams 2.1.0-r5801' in win32gui.GetWindowText(hwnd):
			target_hwnd = hwnd
			rect = win32gui.GetWindowRect(hwnd)
			x = rect[0] + 3
			y = rect[1] + 26
			w = rect[2] - x
			h = rect[3] - y
			print "\t     Name: %s" % win32gui.GetWindowText(hwnd)
			print "\t Location: (%d, %d)" % (x, y)
			print "\t     Size: (%d, %d)" % (w, h)

def classToLabel(cls):
    if cls == 0:
        return 'left'
    elif cls == 1:
        return 'forward'
    else:
        return 'right'

def keyPressByCls(cls):
    if target_hwnd is None or win32gui.GetWindowText(target_hwnd) != 'Speed Dreams 2.1.0-r5801':
        print 'No Game window found!'
        return
    start_ts = current_milli_time()
    print 'KeyPressByCls = ', cls
    if cls == 0:
        win32api.SendMessage(target_hwnd, win32con.WM_KEYDOWN, win32con.VK_UP, 0)
        win32api.SendMessage(target_hwnd, win32con.WM_KEYDOWN, win32con.VK_LEFT, 0)
        while current_milli_time() - start_ts < 300:
            continue
        win32api.SendMessage(target_hwnd, win32con.WM_KEYUP, win32con.VK_LEFT, 0)
        win32api.SendMessage(target_hwnd, win32con.WM_KEYUP, win32con.VK_UP, 0)
    elif cls == 1:
        win32api.SendMessage(target_hwnd, win32con.WM_KEYDOWN, win32con.VK_UP, 0)
        while current_milli_time() - start_ts < 500:
            continue
        win32api.SendMessage(target_hwnd, win32con.WM_KEYUP, win32con.VK_UP, 0)
    else:
        win32api.SendMessage(target_hwnd, win32con.WM_KEYDOWN, win32con.VK_UP, 0)
        win32api.SendMessage(target_hwnd, win32con.WM_KEYDOWN, win32con.VK_RIGHT, 0)
        while current_milli_time() - start_ts < 300:
            continue
        win32api.SendMessage(target_hwnd, win32con.WM_KEYUP, win32con.VK_RIGHT, 0)
        win32api.SendMessage(target_hwnd, win32con.WM_KEYUP, win32con.VK_UP, 0)


def get_net(caffemodel, deploy_file, use_gpu=True):
    """
    Returns an instance of caffe.Net
    Arguments:
    caffemodel -- path to a .caffemodel file
    deploy_file -- path to a .prototxt file
    Keyword arguments:
    use_gpu -- if True, use the GPU for inference
    """
    if use_gpu:
        caffe.set_mode_gpu()
        caffe.set_device(0)

    # load a new model
    return caffe.Net(deploy_file, caffemodel, caffe.TEST)

def get_transformer(deploy_file, mean_file=None):
    """
    Returns an instance of caffe.io.Transformer
    Arguments:
    deploy_file -- path to a .prototxt file
    Keyword arguments:
    mean_file -- path to a .binaryproto file (optional)
    """
    network = caffe_pb2.NetParameter()
    with open(deploy_file) as infile:
        text_format.Merge(infile.read(), network)

    if network.input_shape:
        dims = network.input_shape[0].dim
    else:
        dims = network.input_dim[:4]

    t = caffe.io.Transformer(
            inputs = {'data': dims}
            )
    t.set_transpose('data', (2,0,1)) # transpose to (channels, height, width)

    # color images
    if dims[1] == 3:
        # channel swap
        t.set_channel_swap('data', (2,1,0))

    if mean_file:
        # set mean pixel
        with open(mean_file,'rb') as infile:
            blob = caffe_pb2.BlobProto()
            blob.MergeFromString(infile.read())
            if blob.HasField('shape'):
                blob_dims = blob.shape
                assert len(blob_dims) == 4, 'Shape should have 4 dimensions - shape is "%s"' % blob.shape
            elif blob.HasField('num') and blob.HasField('channels') and \
                    blob.HasField('height') and blob.HasField('width'):
                blob_dims = (blob.num, blob.channels, blob.height, blob.width)
            else:
                raise ValueError('blob does not provide shape or 4d dimensions')
            pixel = np.reshape(blob.data, blob_dims[1:]).mean(1).mean(1)
            t.set_mean('data', pixel)

    return t

def forward_pass(images, net, transformer, batch_size=1):
    """
    Returns scores for each image as an np.ndarray (nImages x nClasses)
    Arguments:
    images -- a list of np.ndarrays
    net -- a caffe.Net
    transformer -- a caffe.io.Transformer
    Keyword arguments:
    batch_size -- how many images can be processed at once
        (a high value may result in out-of-memory errors)
    """
    caffe_images = []
    for image in images:
        if image.ndim == 2:
            caffe_images.append(image[:,:,np.newaxis])
        else:
            caffe_images.append(image)

    caffe_images = np.array(caffe_images)

    dims = transformer.inputs['data'][1:]

    scores = None
    for chunk in [caffe_images[x:x+batch_size] for x in xrange(0, len(caffe_images), batch_size)]:
        new_shape = (len(chunk),) + tuple(dims)
        if net.blobs['data'].data.shape != new_shape:
            net.blobs['data'].reshape(*new_shape)
        for index, image in enumerate(chunk):
            image_data = transformer.preprocess('data', image)
            net.blobs['data'].data[index] = image_data
        output = net.forward()[net.outputs[-1]]
        if scores is None:
            scores = np.copy(output)
        else:
            scores = np.vstack((scores, output))
        print 'Processed %s/%s images ...' % (len(scores), len(caffe_images))

    return scores

# Keyboard relative functions
#

def OnKeyboardEvent(event):
    global stop, left_num, right_num, up_num, label
    global w,h,x,y
    kb_time = current_milli_time()
    print 'MessageName:',event.MessageName
    print 'Time:',kb_time
    print 'Key:', event.Key
    print '---'

    if event.KeyID in (27, 37, 38, 39):
        if event.MessageName == 'key down':
            if event.KeyID == 37:   # left
                left_num += 1
                label='-1'
            elif event.KeyID == 39: # right
                right_num += 1
                label='1'
            elif event.KeyID == 37: # up
                return True
            elif event.KeyID == 27: # ESC
                stop = True
                return True

            im = ImageGrab.grab(bbox=(x, y, w, h))
            im.save(label+'/'+str(kb_time)+'.png')
    else:
        label=None
    # put the key into queue
    # return True to pass the event to other handlers
    return True

def PredictThread():


    idx = 0
    while stop == False:
        print 'Predicting...'
        #print "capture[%d] %d, %d [%d x %d]" % (idx, x, y, w, h)
        start_ts = current_milli_time()
        im = ImageGrab.grab(bbox=(x, y, w, h)) # return a RGB image
        im = im.resize((256,256), Image.BILINEAR)
        # convert image to numpy array
        pix = np.array(im)
        print 'size of matrix = ', pix.shape
        #pix = scipy.misc.imresize(pix, (256, 256), 'bilinear')
        scores = forward_pass([pix], net, transformer)
        guess_action = scores.argmax()
        dur_time_in_ms = current_milli_time() - start_ts
        print 'action = %s, cause %d ms' %(classToLabel(guess_action), dur_time_in_ms)
        keyPressByCls(guess_action)
        idx += 1

# start main function here #
if __name__ == '__main__':
    #freeze_support()

    print "Start!"

    net = get_net(CAFFE_MODE_FILE, DEPLOY_FILE, True)
    transformer = get_transformer(DEPLOY_FILE, MEAN_FILE)

    thread.start_new_thread(PredictThread, ())

    while target_hwnd == None:
        print 'finding target window handler'
        win32gui.EnumWindows(enumHandler, None)
        time.sleep(5)

    # Send key events, works!
    if target_hwnd == None:
        print "No window found!"
        exit()

    # create a hook manager
    hm = pyHook.HookManager()
    # watch for all mouse events
    hm.KeyDown = OnKeyboardEvent
    # set the hook
    hm.HookKeyboard()
    while stop == False:
        pythoncom.PumpWaitingMessages()

    print '=========Summary========='
    print 'Left = ', left_num
    print 'Up = ', up_num
    print 'Right = ', right_num