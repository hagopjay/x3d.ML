import gzip,brotli,lzma,time,json,sys
b=open(sys.argv[1],'rb').read(); r={'raw':len(b)}
t=time.time(); r['gzip9']=len(gzip.compress(b,9,mtime=0)); r['gzip_s']=round(time.time()-t,1)
t=time.time(); r['brotli11']=len(brotli.compress(b,quality=11,lgwin=24)); r['br_s']=round(time.time()-t,1)
print(json.dumps(r),flush=True)
