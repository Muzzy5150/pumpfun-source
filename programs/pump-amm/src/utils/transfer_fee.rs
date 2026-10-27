use crate::*;
use anchor_spl::token_2022::spl_token_2022::{
    extension::transfer_fee::TransferFee,
};

#[derive(Clone, Copy, Debug)]
pub struct DecodedTransferFee {
    pub epoch: u64,
    pub maximum_fee: u64,
    pub transfer_fee_basis_points: u16,
}

impl DecodedTransferFee {
    fn spl_fee(&self) -> TransferFee {
        TransferFee {
            epoch: self.epoch.into(),
            maximum_fee: self.maximum_fee.into(),
            transfer_fee_basis_points: self.transfer_fee_basis_points.into(),
        }
    }
}

pub type TransferFeeData = Option<DecodedTransferFee>;

/// Reads the Token-2022 transfer-fee configuration that applies in the current epoch.
pub fn from_mint(mint: &AccountInfo) -> Result<TransferFeeData> {
    if mint.owner != &anchor_spl::token_2022::ID {
        return Ok(None);
    }
    let data = mint.try_borrow_data()?;
    let fees = decode_transfer_fees(&data)
        .map_err(|_| error!(PumpAmmError::UnsupportedQuoteMint))?;
    let Some((older, newer)) = fees else {
        return Ok(None);
    };
    let epoch = Clock::get()?.epoch;
    Ok(Some(if epoch >= newer.epoch { newer } else { older }))
}

/// Fee withheld by Token-2022 when `amount` is transferred.
///
/// Mints without a transfer-fee extension charge nothing.
pub fn calculate_fee(data: &TransferFeeData, amount: u64) -> Result<u64> {
    match data {
        None => Ok(0),
        Some(fee) => fee
            .spl_fee()
            .calculate_fee(amount)
            .ok_or_else(|| error!(PumpAmmError::Overflow)),
    }
}

/// Amount received after the transfer fee is withheld.
pub fn amount_after_fee(data: &TransferFeeData, amount: u64) -> Result<u64> {
    amount
        .checked_sub(calculate_fee(data, amount)?)
        .ok_or_else(|| error!(PumpAmmError::Overflow))
}

/// Gross amount to send so that `amount` arrives after the transfer fee.
pub fn amount_before_fee(data: &TransferFeeData, amount: u64) -> Result<u64> {
    match data {
        None => Ok(amount),
        Some(fee) => fee
            .spl_fee()
            .calculate_pre_fee_amount(amount)
            .ok_or_else(|| error!(PumpAmmError::Overflow)),
    }
}

/// Harvests withheld Token-2022 transfer fees from `source` into `mint`.
pub fn harvest_to_mint<'info>(
    token_program: &AccountInfo<'info>,
    mint: &AccountInfo<'info>,
    source: &AccountInfo<'info>,
) -> Result<()> {
    anchor_spl::token_2022_extensions::transfer_fee::harvest_withheld_tokens_to_mint(
        CpiContext::new(
            token_program.clone(),
            anchor_spl::token_2022_extensions::transfer_fee::HarvestWithheldTokensToMint {
                token_program_id: token_program.clone(),
                mint: mint.clone(),
            },
        ),
        vec![source.clone()],
    )
}

/// Extract the epoch fee pair while validating the Token-2022 mint TLV envelope.
fn decode_transfer_fees(data: &[u8]) -> std::result::Result<Option<(DecodedTransferFee, DecodedTransferFee)>, ()> {
    if data.len() == 82 {
        return Ok(None);
    }
    if data.len() < 167 || data[82..165].iter().any(|byte| *byte != 0) || data[165] != 1 {
        return Err(());
    }
    let mut remaining = &data[166..];
    let mut fees = None;
    while remaining.len() >= 2 {
        let kind = u16::from_le_bytes(remaining[..2].try_into().unwrap());
        if kind == 0 {
            break;
        }
        if remaining.len() < 4 {
            return Err(());
        }
        let length = u16::from_le_bytes(remaining[2..4].try_into().unwrap()) as usize;
        let value = remaining.get(4..4 + length).ok_or(())?;
        if kind == 1 {
            if fees.is_some() || length < 108 {
                return Err(());
            }
            let read_fee = |bytes: &[u8]| DecodedTransferFee {
                epoch: u64::from_le_bytes(bytes[..8].try_into().unwrap()),
                maximum_fee: u64::from_le_bytes(bytes[8..16].try_into().unwrap()),
                transfer_fee_basis_points: u16::from_le_bytes(bytes[16..18].try_into().unwrap()),
            };
            fees = Some((read_fee(&value[72..90]), read_fee(&value[90..108])));
        }
        remaining = &remaining[4 + length..];
    }
    Ok(fees)
}
