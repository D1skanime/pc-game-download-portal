use std::collections::BTreeMap;

/// A validated HTTP(S) authority configured by the native client.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ConfiguredOrigin {
    value: String,
}

impl ConfiguredOrigin {
    pub fn parse(value: &str) -> Result<Self, HttpBoundaryError> {
        let (scheme, authority) = value
            .split_once("://")
            .ok_or(HttpBoundaryError::InvalidOrigin)?;
        if !matches!(scheme, "http" | "https")
            || authority.is_empty()
            || authority.contains(['/', '?', '#', '@'])
            || authority.chars().any(char::is_whitespace)
        {
            return Err(HttpBoundaryError::InvalidOrigin);
        }
        Ok(Self {
            value: value.to_owned(),
        })
    }

    pub fn join_relative(&self, route: &str) -> Result<String, HttpBoundaryError> {
        if !route.starts_with('/') || route.starts_with("//") || route.contains(['?', '#']) {
            return Err(HttpBoundaryError::InvalidOrigin);
        }
        Ok(format!("{}{route}", self.value))
    }

    pub fn contains_url(&self, url: &str) -> bool {
        url.strip_prefix(&self.value)
            .is_some_and(|path| path.starts_with('/') && !path.starts_with("//"))
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum HttpBoundaryError {
    InvalidOrigin,
}

/// Transport-neutral request. Headers never include browser state.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct HttpRequest {
    pub url: String,
    pub headers: BTreeMap<String, String>,
}

/// Transport-neutral response, including the final URL after any transport redirect handling.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct HttpResponse {
    pub status: u16,
    pub headers: BTreeMap<String, String>,
    pub body: Vec<u8>,
    pub final_url: Option<String>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct HttpTransportError;

/// The native adapter seam. Implementations must not forward credentials across origins.
pub trait HttpTransport {
    fn execute(&mut self, request: HttpRequest) -> Result<HttpResponse, HttpTransportError>;
}
