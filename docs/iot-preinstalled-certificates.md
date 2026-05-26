# Pre-installed Device Certificates for IoT

How IoT products implement X.509 certificates burned into devices during manufacturing.

## Manufacturing Process

### 1. Key Generation (Secure Element)

Keys are generated inside secure hardware where the private key cannot be extracted:

- **Secure Elements**: Microchip ATECC608B, Infineon OPTIGA, STSAFE
- **TPM Chips**: Trusted Platform Modules for key storage
- **HSMs**: Hardware Security Modules on the production line

```bash
# At the factory, each device generates keys inside a secure element
device_id=$(get_hardware_serial)  # unique per device
# Private key never leaves the secure element
```

### 2. Certificate Signing Request (CSR)

The device creates a CSR bound to its unique identity:

```bash
csr=$(openssl req -new -key device_key.pem \
  -subj "/CN=${device_id}.local/O=IoTProduct/C=US")
```

### 3. Certificate Issuance

**Internal PKI (Most Common):**
```bash
openssl x509 -req -in device.csr -CA ca.crt -CAkey ca.key \
  -set_serial 0${device_id_hash} -out device.crt \
  -extfile <(echo "subjectAltName=DNS:${device_id}.local")
```

**External Commercial CA:**
- Submit CSR via EST (RFC 7037) or SCEP protocol
- Device gets publicly-trusted certificate

### 4. Programming Step

During manufacturing, the following are programmed into the device:
- Device certificate (public data)
- Intermediate certificate chain
- Device's unique private key (if not in secure element)

## In-Field Operation

```javascript
// Device starts with HTTPS server using pre-installed certificate
const https = require('https');

const server = https.createServer({
  cert: fs.readFileSync('/etc/device.crt'),
  key: fs.readFileSync('/etc/device.key'),  // or accessed via secure element API
}, app);

server.listen(443);
```

## Trust Distribution

### For Local mDNS Devices
- Root CA certificate bundled with companion apps
- No public trust required since communications are local-only

### Trust Models
1. **Companion App**: Bundle root CA with mobile app binary
2. **Browser Access**: User installs root CA once in browser/OS trust store
3. **Enterprise**: Push root CA via MDM or Group Policy

## Protocols and Tools

| Protocol | Purpose | RFC |
|----------|---------|-----|
| EST | Enrollment over Secure Transport | 7037 |
| SCEP | Certificate enrollment | - |
| CMP | Certificate Management Protocol | 4210 |

### PKI Infrastructure
- **Microsoft ADCS**: Active Directory Certificate Services
- **EJBCA**: Open source PKI
- **AWS CloudHSM**: Cloud-based HSM for PKI

## Security Considerations

1. **Secure Element Required**: Private keys must never be extractable
2. **Unique Identity**: Each certificate bound to hardware serial
3. **Revocation**: Plan for certificate lifecycle (CRL/OCSP)
4. **Firmware Updates**: Certificate replacement mechanism

## Alternative: Bootstrap Certificates

For devices that need to obtain certificates post-manufacturing:

1. Device ships with bootstrap certificate
2. First cloud connection verifies device identity
3. Cloud issues proper certificate for local use
4. Old bootstrap cert revoked