import json,sys
m=json.load(open('/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/spine/manifest_clean_ondisk.json'))
m=[o for o in m if o['enc']=='xml']
m.sort(key=lambda o:o['bytes'])
json.dump([{'id':o['id'],'path':o['path'],'bytes':o['bytes'],'kind':o['kind']} for o in m],open('/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/spine/bpy/items_all.json','w'))
json.dump([{'id':o['id'],'path':o['path'],'bytes':o['bytes'],'kind':o['kind']} for o in m[:3]]+[{'id':o['id'],'path':o['path'],'bytes':o['bytes'],'kind':o['kind']} for o in m if o['kind']=='hand'][:2],open('/tmp/claude-0/-home-user/265b8e8b-423c-5c89-85e0-1bdddc0f5797/scratchpad/spine/bpy/items_test.json','w'))
print(len(m))
