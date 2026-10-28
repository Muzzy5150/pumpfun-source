extern crate pump_recovered;
extern crate anchor_lang;
use pump_recovered::buy_v2::BuyV2;
use pump_recovered::trade::SellV3;
use pump_recovered::trade_types::BondingCurve;
use anchor_lang::prelude::*;
pub fn v2_curve()->usize { std::mem::offset_of!(BuyV2<'static>,bonding_curve) }
pub fn v2_system()->usize { std::mem::offset_of!(BuyV2<'static>,system_program) }
pub fn v2_user()->usize { std::mem::offset_of!(BuyV2<'static>,user) }
pub fn v3_curve()->usize { std::mem::offset_of!(SellV3<'static>,bonding_curve) }
pub fn v3_system()->usize { std::mem::offset_of!(SellV3<'static>,system_program) }
pub fn v3_user()->usize { std::mem::offset_of!(SellV3<'static>,user) }
pub fn curve_info<'a,'info>(x:&'a Account<'info,BondingCurve>)->&'a AccountInfo<'info>{x.as_ref()}
pub fn v2_quote_source()->usize { std::mem::offset_of!(BuyV2<'static>,associated_quote_user) }
pub fn v2_quote_destination()->usize { std::mem::offset_of!(BuyV2<'static>,associated_quote_bonding_curve) }
pub fn v3_quote_source()->usize { std::mem::offset_of!(SellV3<'static>,associated_quote_user) }
pub fn v3_quote_destination()->usize { std::mem::offset_of!(SellV3<'static>,associated_quote_bonding_curve) }
#[used]
static OFFSETS:[fn()->usize;10]=[v2_curve,v2_system,v2_user,v3_curve,v3_system,v3_user,v2_quote_source,v2_quote_destination,v3_quote_source,v3_quote_destination];
#[used]
static GETTER:for<'a,'info>fn(&'a Account<'info,BondingCurve>)->&'a AccountInfo<'info>=curve_info;
