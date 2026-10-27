include!("interface_definition.rs");






    recovered_interfaces!();






    recovered_pool!();

pub use anchor_spl::token_interface;

pub mod legacy_event_utils {
use anchor_lang::prelude::*;
use super::cpi_interface::pump::events::*;
        /// An enum that includes all events of the declared program as a tuple variant.
        ///
        /// See [`Self::try_from_bytes`] to create an instance from bytes.
        pub enum Event {
            CreateEvent(CreateEvent),
        }

        impl Event {
            /// Try to create an event based on the given bytes.
            ///
            /// This method returns an error if the discriminator of the given bytes don't match
            /// with any of the existing events, or if the deserialization fails.
            pub fn try_from_bytes(bytes: &[u8]) -> Result<Self> {
                Self::try_from(bytes)
            }
        }

        impl TryFrom<&[u8]> for Event {
            type Error = anchor_lang::error::Error;

            fn try_from(value: &[u8]) -> Result<Self> {
                            if value.starts_with(CreateEvent::DISCRIMINATOR) {
                return CreateEvent::try_from_slice(&value[CreateEvent::DISCRIMINATOR.len()..])
                    .map(Self::CreateEvent)
                    .map_err(Into::into)
            }

                Err(ProgramError::InvalidArgument.into())
            }
        }
}
