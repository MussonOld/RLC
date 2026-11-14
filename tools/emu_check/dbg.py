import random, struct, sys
import harness as h
h.init(); syms=h.PORT[1]
def runboth(setup, orig, port, args=(), fargs=()):
    mo=h.Machine(h.PORT[0]); setup(mo); mp=h.Machine(h.PORT[0]); setup(mp)
    base=mo.ram(); eo=ep=None
    try: mo.call(orig,args,fargs)
    except Exception as e: eo=repr(e)
    try: mp.call(syms[port],args,fargs)
    except Exception as e: ep=repr(e)
    def mods(m):
        cur=m.ram(); out={}
        for i in range(0,len(cur)-0x2000,4):
            if cur[i:i+4]!=base[i:i+4]: out[0x20000000+i]=cur[i:i+4].hex()
        return out
    return mods(mo),mods(mp),eo,ep,mo.trace,mp.trace
def show(tag,seed,mo,mp,eo,ep,to,tp):
    only_o={hex(k):v for k,v in mo.items() if mp.get(k)!=v}; only_p={hex(k):v for k,v in mp.items() if mo.get(k)!=v}
    print(tag,"seed",seed,"\n  orig-only",only_o,"\n  port-only",only_p,"\n  exc",eo,ep,"\n  trace",len(to),len(tp))
