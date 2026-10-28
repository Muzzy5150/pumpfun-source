use anchor_lang::prelude::*;
use crate::{Global,PumpError,trade_types::BondingCurve};
pub const METAPLEX:Pubkey=anchor_lang::solana_program::pubkey!("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s");
use anchor_spl::metadata::MetadataAccount as CreatorMetadata;
#[event_cpi]
#[derive(Accounts)]pub struct SetCreator<'info>{
 pub set_creator_authority:Signer<'info>,
 #[account(seeds=[b"global"],bump,has_one=set_creator_authority @ PumpError::NotAuthorized)]pub global:Account<'info,Global>,
 pub mint:Account<'info,anchor_spl::token::Mint>,
 #[account(seeds=[b"metadata",METAPLEX.as_ref(),mint.key().as_ref()],bump,seeds::program=METAPLEX)]pub metadata:Account<'info,CreatorMetadata>,
 #[account(mut,seeds=[b"bonding-curve",mint.key().as_ref()],bump)]pub bonding_curve:Account<'info,BondingCurve>,
}
#[event_cpi]
#[derive(Accounts)]pub struct SetMetaplexCreator<'info>{
 pub mint:Account<'info,anchor_spl::token::Mint>,
 #[account(seeds=[b"metadata",METAPLEX.as_ref(),mint.key().as_ref()],bump,seeds::program=METAPLEX)]pub metadata:Account<'info,CreatorMetadata>,
 #[account(mut,seeds=[b"bonding-curve",mint.key().as_ref()],bump)]pub bonding_curve:Account<'info,BondingCurve>,
}
#[event]#[derive(Clone)]pub struct SetCreatorEvent{pub timestamp:i64,pub mint:Pubkey,pub bonding_curve:Pubkey,pub creator:Pubkey}
#[event]#[derive(Clone)]pub struct SetMetaplexCreatorEvent{pub timestamp:i64,pub mint:Pubkey,pub bonding_curve:Pubkey,pub metadata:Pubkey,pub creator:Pubkey}
#[path="creator/set_creator.rs"] mod set_creator_impl;
#[path="creator/set_metaplex_creator.rs"] mod set_metaplex_creator_impl;
pub use set_creator_impl::set;
pub use set_metaplex_creator_impl::sync;
