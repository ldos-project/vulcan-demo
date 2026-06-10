from collections import OrderedDict

def init_hook(params):
    return OrderedDict()

def hit_hook(data, req):
    data.move_to_end(req.obj_id, last=True)

def miss_hook(data, req):
    data[req.obj_id] = req.obj_size

def eviction_hook(data, req):
    return data.popitem(last=False)[0]

def remove_hook(data, obj_id):
    data.pop(obj_id, None)