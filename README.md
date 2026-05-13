# nam-box

## Development guide

### Cloudflare tunnel configuration

The development environment includes [cloudflared tunneling](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/) to enable access to the application running in it, especially from contexts like GitHub Codespaces. Steps to prepare for this tunneling are as follows:

1. [Onboard a domain to Cloudflare](https://developers.cloudflare.com/dns/zone-setups/full-setup/setup/), if not already configured.
1. Export that domain name in the terminal as `NAM_BOX_TUNNEL_DOMAIN`, e.g. `export NAM_BOX_TUNNEL_DOMAIN=domainname.tld` (optionally, set this as a Codespaces secret instead). Note that this likely must not be a subdomain, as ["by default, Cloudflare Universal SSL certificates only cover your apex domain and one level of subdomain"](https://developers.cloudflare.com/ssl/troubleshooting/version-cipher-mismatch/#multi-level-subdomains).
1. Execute `./.devcontainer/scripts/prep-cloudflared`
1. Follow the link produced in the script output, and select the domain to which to attach the tunnel.

## Contributing
