# dotgen

> Community .gen name registry on GenLayer Bradbury

Register a human-readable `.gen` name, point it to your wallet, and attach a profile — bio, avatar, URL. Every registration is validated by an AI Intelligent Contract before it lands on-chain.

**Contract:** `0xD7123F37FE4FCBAF4Be37fBdEEB6f8AaC22042B3`

---

## What it does

- **Register a `.gen` name** — AI validates it first. Blocks impersonation of known people and protocols (`vitalik.gen`, `ethereum.gen`, `metamask.gen`) and rejects inappropriate names before they touch the chain
- **Point it anywhere** — resolves to any wallet address, not just yours
- **Full profile** — avatar emoji, bio, website URL stored on-chain
- **Reverse lookup** — look up who owns a `.gen` name, or look up a wallet's primary name
- **Set primary** — if you own multiple names, set which one is primary
- **Release** — give a name back to the pool

---

## AI validation

Every `register()` call runs through `prompt_non_comparative` consensus:

```python
def validate_name():
    prompt = (
        "You are a domain name registrar for the GenLayer ecosystem.\n"
        "REJECT if the name impersonates a well-known person or brand,\n"
        "contains hate speech, or is a government/official institution.\n"
        "APPROVE if it's a creative handle, nickname, or personal brand.\n\n"
        "Reply ONLY with: APPROVED or REJECTED: <reason>"
    )
    return gl.nondet.exec_prompt(prompt)

verdict = gl.eq_principle.prompt_non_comparative(validate_name, ...)
```

If the AI returns `REJECTED`, the transaction reverts with the reason. No name lands on-chain without passing the check.

---

## Contract methods

| Method | Description |
|--------|-------------|
| `register(name, address, url, avatar, bio)` | Register a `.gen` name with AI validation |
| `update_record(name, url, avatar, bio)` | Update profile data for a name you own |
| `transfer(name, new_owner)` | Transfer ownership to another address |
| `set_primary(name)` | Set your primary `.gen` name |
| `release(name)` | Release a name back to the pool |
| `get_record(name)` | Full lookup for a `.gen` name |
| `get_all_names()` | Browse all registered names |
| `is_available(name)` | Returns AVAILABLE / TAKEN / INVALID |
| `get_name_by_address(address)` | Reverse lookup: address → primary name |

---

## Repo structure

```
dotgen/
├── gns.py           # Intelligent Contract
├── gns_site.html    # Frontend (single file)
└── README.md
```

### GenLayer Bradbury network
```
RPC:      https://rpc-bradbury.genlayer.com
Chain ID: 4221
Currency: GEN
Explorer: https://explorer-bradbury.genlayer.com
```

---

## Limitations

Names are stored in this contract's on-chain state. They are not protocol-level — other dApps can read them by querying `get_record()` or `get_name_by_address()` directly, but there is no automatic resolution at the wallet or RPC level (like ENS on Ethereum).

---

Built by [@iniwuraakuru](https://github.com/iniwuraakuru) · GenLayer Bradbury Builder Program
