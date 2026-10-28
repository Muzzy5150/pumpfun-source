# shared: replace the hand-built create_pool call (L06 lines 327-328) with a 2-line helper call; append HELPER
f='migrate_v2.rs'
n0=lines(f)
s=(src/f).read_text().split('\n')
i=[k for k,l in enumerate(s) if l.startswith(' let creator=a.bonding_curve.creator;let mut data=vec![233,146,209')]
assert len(i)==1; i=i[0]
assert s[i+1].startswith(' call(&am,&[(&pool,false,true),(&cfg,false,false),(&pa,true,true),(&base_mint,false,false),(&wsol,false,false),(&lp,false,true)')
s[i]=CALL1; s[i+1]=CALL2
(src/f).write_text('\n'.join(s).rstrip('\n')+'\n'+HELPER+'\n')
