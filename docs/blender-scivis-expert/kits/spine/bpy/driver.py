import subprocess, sys, json, os, time, signal
PY='/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/v/bin/python'
items_f, out_f, exp_dir, mode = sys.argv[1:5]
STALE=int(sys.argv[5]) if len(sys.argv)>5 else 180
items=json.load(open(items_f))
def done_ids():
    d=set()
    if os.path.exists(out_f):
        for l in open(out_f):
            try: d.add(json.loads(l)['id'])
            except: pass
    return d
while True:
    d=done_ids()
    todo=[i for i in items if i['id'] not in d]
    if not todo: break
    p=subprocess.Popen([PY,'-I','/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/spine/bpy/worker.py',items_f,out_f,exp_dir,mode],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
    last=len(d); last_t=time.time()
    while p.poll() is None:
        time.sleep(2)
        n=len(done_ids())
        if n>last: last=n; last_t=time.time()
        if time.time()-last_t>STALE:
            os.killpg(p.pid,signal.SIGKILL); p.wait(); break
    d2=done_ids()
    todo2=[i for i in items if i['id'] not in d2]
    if todo2 and len(d2)==len(d):   # no progress -> the first todo item killed the worker
        bad=todo2[0]
        with open(out_f,'a') as f:
            f.write(json.dumps({'id':bad['id'],'path':bad['path'],'bytes':bad.get('bytes'),'worker_died':True,'rc':p.returncode})+'\n')
print('driver done')
