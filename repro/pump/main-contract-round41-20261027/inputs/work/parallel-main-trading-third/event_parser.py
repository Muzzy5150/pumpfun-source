import base64,struct
TRADE=[('mint','pubkey'),('sol_amount','u64'),('token_amount','u64'),('is_buy','bool'),('user','pubkey'),('timestamp','i64'),('virtual_sol_reserves','u64'),('virtual_token_reserves','u64'),('real_sol_reserves','u64'),('real_token_reserves','u64'),('fee_recipient','pubkey'),('fee_basis_points','u64'),('fee','u64'),('creator','pubkey'),('creator_fee_basis_points','u64'),('creator_fee','u64'),('track_volume','bool'),('total_unclaimed_tokens','u64'),('total_claimed_tokens','u64'),('current_sol_volume','u64'),('last_update_timestamp','i64'),('ix_name','string'),('mayhem_mode','bool'),('cashback_fee_basis_points','u64'),('cashback','u64'),('buyback_fee_basis_points','u64'),('buyback_fee','u64'),('shareholders','shares'),('quote_mint','pubkey'),('quote_amount','u64'),('virtual_quote_reserves','u64'),('real_quote_reserves','u64'),('holder_rewards_bps','u64'),('holder_rewards','u64'),('creator_fee_unclaimed','u64'),('unparsed_trailing_field','u64')]
def decode(event):
 data=base64.b64decode(event[14:] if event.startswith('Program data: ') else event);disc=data[:8].hex();o=8;r={'discriminator':disc}
 if disc=='bddb7fd34ee661ee': fields=TRADE;r['event']='trade'
 elif disc=='5f72619cd42e9808':fields=[('user','pubkey'),('mint','pubkey'),('bonding_curve','pubkey'),('timestamp','i64'),('quote_mint','pubkey')];r['event']='complete'
 elif disc=='6fb06d8b316cd5fb':fields=[('user','pubkey'),('mint','pubkey'),('bonding_curve','pubkey'),('quote_mint','pubkey'),('timestamp','i64')]+[(n,'u64') for n in ['base_out','quote_in','fee_basis_points','fee','creator_fee_basis_points','creator_fee','buyback_fee','pool_base_reserves_before','pool_quote_reserves_before','pool_base_reserves_after','pool_quote_reserves_after']];r['event']='post_complete'
 else:return r|{'raw':data.hex()}
 for name,kind in fields:
  if kind in ('u64','i64'):r[name]=int.from_bytes(data[o:o+8],'little',signed=kind=='i64');o+=8
  elif kind=='pubkey':r[name]=data[o:o+32].hex();o+=32
  elif kind=='bool':r[name]=bool(data[o]);o+=1
  elif kind=='string':n=int.from_bytes(data[o:o+4],'little');o+=4;r[name]=data[o:o+n].decode();o+=n
  elif kind=='shares':n=int.from_bytes(data[o:o+4],'little');o+=4;r[name]=data[o:o+34*n].hex();o+=34*n
 assert o==len(data),(o,len(data),r)
 return r
