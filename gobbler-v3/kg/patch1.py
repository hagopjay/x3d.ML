p='kg/extract.py'
s=open(p).read()
a="""    try:
        r = gem.jcall(MODEL, prompt(ch), system=SYS, temperature=0.55, max_out=12000, tag='extract:%s:%d' % (ch['doc'][:30], k), cap=float(os.environ.get('CAP', '15')))
    except Exception as e:
        return 'ERR %s %s' % (ch['id'], str(e)[:80])"""
b="""    r = None; err = ''
    for att in range(3):
        try:
            r = gem.jcall(MODEL, prompt(ch), system=SYS, temperature=0.55, max_out=12000, tag='extract:%s:%d' % (ch['doc'][:30], k), cap=float(os.environ.get('CAP', '15')))
            break
        except Exception as e:
            err = str(e)[:80]
    if r is None:
        return 'ERR %s %s' % (ch['id'], err)"""
assert a in s
open(p,'w').write(s.replace(a,b))
