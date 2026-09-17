use romm_download_core::ConfiguredOrigin;
use serde::{Deserialize, Serialize};

const ROMS_READ_SCOPE: &str = "roms.read";

pub trait DeviceAuthTransport {
    fn send(
        &mut self,
        method: &str,
        url: &str,
        body: &str,
    ) -> Result<DeviceAuthHttpResponse, ()>;
}

pub trait TokenStore {
    fn save(&mut self, token: &str) -> Result<(), ()>;
    #[allow(dead_code)]
    fn load(&self) -> Result<Option<String>, ()>;
    fn clear(&mut self) -> Result<(), ()>;
}

#[derive(Clone, Debug)]
pub struct DeviceAuthHttpResponse {
    status: u16,
    body: String,
}

impl DeviceAuthHttpResponse {
    #[cfg(test)]
    #[allow(dead_code)]
    pub fn json(status: u16, body: &str) -> Self {
        Self {
            status,
            body: body.to_owned(),
        }
    }
}

#[allow(dead_code)]
pub struct ReqwestDeviceAuthTransport {
    client: reqwest::blocking::Client,
}

impl ReqwestDeviceAuthTransport {
    #[allow(dead_code)]
    pub fn new() -> Result<Self, ()> {
        reqwest::blocking::Client::builder()
            .redirect(reqwest::redirect::Policy::none())
            .build()
            .map(|client| Self { client })
            .map_err(|_| ())
    }
}

impl DeviceAuthTransport for ReqwestDeviceAuthTransport {
    fn send(
        &mut self,
        method: &str,
        url: &str,
        body: &str,
    ) -> Result<DeviceAuthHttpResponse, ()> {
        let request = self
            .client
            .request(method.parse().map_err(|_| ())?, url)
            .header(reqwest::header::CONTENT_TYPE, "application/json")
            .body(body.to_owned());
        let response = request.send().map_err(|_| ())?;
        Ok(DeviceAuthHttpResponse {
            status: response.status().as_u16(),
            body: response.text().map_err(|_| ())?,
        })
    }
}

#[allow(dead_code)]
pub struct KeyringTokenStore {
    entry: keyring::Entry,
}

impl KeyringTokenStore {
    #[allow(dead_code)]
    pub fn new() -> Result<Self, ()> {
        keyring::Entry::new("org.romm.desktop", "device-token")
            .map(|entry| Self { entry })
            .map_err(|_| ())
    }
}

impl TokenStore for KeyringTokenStore {
    fn save(&mut self, token: &str) -> Result<(), ()> {
        self.entry.set_password(token).map_err(|_| ())
    }

    fn load(&self) -> Result<Option<String>, ()> {
        match self.entry.get_password() {
            Ok(token) => Ok(Some(token)),
            Err(_) => Ok(None),
        }
    }

    fn clear(&mut self) -> Result<(), ()> {
        let _ = self.entry.delete_credential();
        Ok(())
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
pub enum AuthState {
    Pairing,
    Paired,
    AuthRequired,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct PairingInfo {
    pub user_code: String,
    pub verification_url: String,
    pub expires_at: u64,
    pub interval_seconds: u64,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
pub struct AuthSnapshot {
    pub state: AuthState,
}

struct PendingPairing {
    device_code: String,
    expires_at: u64,
    interval_seconds: u64,
    next_poll_at: u64,
}

pub struct DeviceAuthClient<T: DeviceAuthTransport, S: TokenStore> {
    origin: ConfiguredOrigin,
    transport: T,
    store: S,
    pending: Option<PendingPairing>,
    state: AuthState,
}

impl<T: DeviceAuthTransport, S: TokenStore> DeviceAuthClient<T, S> {
    pub fn new(origin: &str, transport: T, store: S) -> Result<Self, ()> {
        Ok(Self {
            origin: ConfiguredOrigin::parse(origin).map_err(|_| ())?,
            transport,
            store,
            pending: None,
            state: AuthState::AuthRequired,
        })
    }

    pub fn start(
        &mut self,
        client_device_identifier: &str,
        name: &str,
        platform: &str,
        client_version: &str,
        now: u64,
    ) -> Result<PairingInfo, ()> {
        let url = self
            .origin
            .join_relative("/api/auth/device/init")
            .map_err(|_| ())?;
        let body = serde_json::json!({
            "client_device_identifier": client_device_identifier,
            "name": name,
            "client": "romm-desktop",
            "platform": platform,
            "client_version": client_version,
            "requested_scopes": [ROMS_READ_SCOPE],
        })
        .to_string();
        let response = self.transport.send("POST", &url, &body)?;
        if response.status != 201 {
            self.require_repair()?;
            return Err(());
        }
        let parsed: DeviceInitResponse = serde_json::from_str(&response.body).map_err(|_| ())?;
        let expires_at = now.checked_add(parsed.expires_in).ok_or(())?;
        let verification_url = self.origin.join_relative(&parsed.verification_path).map_err(|_| ())?;
        self.pending = Some(PendingPairing {
            device_code: parsed.device_code,
            expires_at,
            interval_seconds: parsed.interval,
            next_poll_at: now.checked_add(parsed.interval).ok_or(())?,
        });
        self.state = AuthState::Pairing;
        Ok(PairingInfo {
            user_code: parsed.user_code,
            verification_url,
            expires_at,
            interval_seconds: parsed.interval,
        })
    }

    pub fn poll(&mut self, now: u64) -> Result<AuthState, ()> {
        let Some(pending) = self.pending.as_ref() else {
            return Ok(self.state);
        };
        if now >= pending.expires_at {
            self.require_repair()?;
            return Ok(self.state);
        }
        if now < pending.next_poll_at {
            return Ok(self.state);
        }
        let device_code = pending.device_code.clone();
        let url = self
            .origin
            .join_relative("/api/auth/device/token")
            .map_err(|_| ())?;
        let body = serde_json::json!({ "device_code": device_code }).to_string();
        let response = self.transport.send("POST", &url, &body)?;
        if let Some(pending) = self.pending.as_mut() {
            pending.next_poll_at = now.checked_add(pending.interval_seconds).ok_or(())?;
        }
        match response.status {
            200 => {
                let token: DeviceTokenResponse = serde_json::from_str(&response.body).map_err(|_| ())?;
                if !token.access_token.starts_with("rmm_") {
                    self.require_repair()?;
                } else {
                    self.store.save(&token.access_token)?;
                    self.pending = None;
                    self.state = AuthState::Paired;
                }
            }
            401 | 403 => self.require_repair()?,
            _ => {}
        }
        Ok(self.state)
    }

    pub fn snapshot(&self) -> AuthSnapshot {
        AuthSnapshot { state: self.state }
    }

    #[cfg(test)]
    #[allow(dead_code)]
    pub fn token_is_stored(&self) -> Result<bool, ()> {
        Ok(self.store.load()?.is_some())
    }

    fn require_repair(&mut self) -> Result<(), ()> {
        self.pending = None;
        self.store.clear()?;
        self.state = AuthState::AuthRequired;
        Ok(())
    }

}

#[derive(Deserialize)]
struct DeviceInitResponse {
    device_code: String,
    user_code: String,
    verification_path: String,
    expires_in: u64,
    interval: u64,
}

#[derive(Deserialize)]
struct DeviceTokenResponse {
    access_token: String,
}
