# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
import json
from genlayer import *


class DotGen(gl.Contract):
    """
    dotgen — community .gen name registry on GenLayer Bradbury.
    AI validates every name registration — blocks impersonation
    and inappropriate names before they land on-chain.
    """

    # ── Storage ──────────────────────────────────────────────
    records_json:   str  # {name: {owner, address, url, avatar, bio, registered_at}}
    reverse_json:   str  # {address: primary_name}
    owner:          str

    MIN_LEN = 3
    MAX_LEN = 32

    def __init__(self):
        self.owner        = str(gl.message.sender_address).lower().strip()
        self.records_json = "{}"
        self.reverse_json = "{}"

    # ── Helpers ──────────────────────────────────────────────
    def _records(self) -> dict: return json.loads(self.records_json)
    def _reverse(self) -> dict: return json.loads(self.reverse_json)
    def _addr(self)    -> str:  return str(gl.message.sender_address).lower().strip()
    def _save_records(self, d): self.records_json = json.dumps(d)
    def _save_reverse(self, d): self.reverse_json = json.dumps(d)

    def _clean_name(self, name: str) -> str:
        return name.strip().lower().replace(".gen", "").replace(" ", "")

    # ── Views ─────────────────────────────────────────────────

    @gl.public.view
    def get_record(self, name: str) -> str:
        records = self._records()
        key     = self._clean_name(name)
        r       = records.get(key)
        if not r:
            return "NOT_FOUND"
        return json.dumps(r)

    @gl.public.view
    def is_available(self, name: str) -> str:
        records = self._records()
        key     = self._clean_name(name)
        if len(key) < self.MIN_LEN or len(key) > self.MAX_LEN:
            return "INVALID"
        for ch in key:
            if not (ch.isalnum() or ch == "-" or ch == "_"):
                return "INVALID"
        if records.get(key):
            return "TAKEN"
        return "AVAILABLE"

    @gl.public.view
    def get_name_by_address(self, address: str) -> str:
        reverse = self._reverse()
        return reverse.get(address.lower().strip(), "")

    @gl.public.view
    def get_all_names(self) -> str:
        records = self._records()
        if not records:
            return "[]"
        result = []
        for name, r in records.items():
            result.append({
                "name":    name,
                "owner":   r.get("owner", ""),
                "address": r.get("address", ""),
                "url":     r.get("url", ""),
                "avatar":  r.get("avatar", ""),
                "bio":     r.get("bio", ""),
            })
        return json.dumps(result)

    @gl.public.view
    def get_owner(self) -> str:
        return self.owner

    # ── Writes ────────────────────────────────────────────────

    @gl.public.write
    def register(self, name: str, address: str,
                 url: str, avatar: str, bio: str):
        """
        Register a .gen name. AI validates the name is appropriate
        and not impersonating a known person or brand before
        it is stored on-chain.
        """
        key     = self._clean_name(name)
        caller  = self._addr()
        records = self._records()

        if len(key) < self.MIN_LEN:
            raise Exception(f"Name too short (minimum {self.MIN_LEN} characters)")
        if len(key) > self.MAX_LEN:
            raise Exception(f"Name too long (maximum {self.MAX_LEN} characters)")
        for ch in key:
            if not (ch.isalnum() or ch == "-" or ch == "_"):
                raise Exception("Name can only contain letters, numbers, hyphens, and underscores")
        if records.get(key):
            raise Exception(f"{key}.gen is already registered")

        # Resolve address — default to caller if blank
        target_addr = address.strip() if address.strip() else caller

        # ── AI validation ──────────────────────────────────
        def validate_name():
            prompt = (
                "You are a domain name registrar for the GenLayer blockchain ecosystem (.gen domains).\n"
                "Evaluate if this name is appropriate to register:\n\n"
                "NAME: " + key + ".gen\n"
                "REGISTRANT ADDRESS: " + caller + "\n\n"
                "REJECT if the name:\n"
                "- Is a well-known person's name (vitalik, satoshi, elonmusk, etc.)\n"
                "- Impersonates a major brand, protocol, or company "
                "  (ethereum, bitcoin, genlayer, uniswap, metamask, etc.)\n"
                "- Contains hate speech, slurs, or explicit content\n"
                "- Is a government entity or official institution\n\n"
                "APPROVE if the name:\n"
                "- Is a creative handle, nickname, or brand name\n"
                "- References a concept, animal, object, or abstract term\n"
                "- Could plausibly be a personal username\n\n"
                "Reply with ONLY one of these two formats:\n"
                "APPROVED\n"
                "REJECTED: <one short reason>\n\n"
                "Nothing else."
            )
            return gl.nondet.exec_prompt(prompt)

        verdict = str(gl.eq_principle.prompt_non_comparative(
            validate_name,
            task="Decide if a .gen domain name is appropriate to register.",
            criteria=(
                "Reply is either 'APPROVED' or 'REJECTED: <reason>'. "
                "Block impersonation of famous people, major crypto protocols, "
                "and hate speech. Allow creative personal handles."
            ),
        )).strip()

        if verdict.upper().startswith("REJECTED"):
            reason = verdict[9:].strip(": ").strip() or "Name not allowed"
            raise Exception(f"Registration rejected: {reason}")

        # ── Store record ───────────────────────────────────
        records[key] = {
            "name":    key,
            "owner":   caller,
            "address": target_addr,
            "url":     url.strip(),
            "avatar":  avatar.strip(),
            "bio":     bio.strip()[:200],
        }
        self._save_records(records)

        # Set as primary name if none exists
        reverse = self._reverse()
        if caller not in reverse:
            reverse[caller] = key
            self._save_reverse(reverse)

    @gl.public.write
    def update_record(self, name: str, url: str,
                      avatar: str, bio: str):
        """Update the URL, avatar, and bio for a .gen name you own."""
        key     = self._clean_name(name)
        caller  = self._addr()
        records = self._records()
        if key not in records:
            raise Exception(f"{key}.gen is not registered")
        if records[key]["owner"] != caller:
            raise Exception("You don't own this name")
        records[key]["url"]    = url.strip()
        records[key]["avatar"] = avatar.strip()
        records[key]["bio"]    = bio.strip()[:200]
        self._save_records(records)

    @gl.public.write
    def transfer(self, name: str, new_owner: str):
        """Transfer a .gen name to a new address."""
        key       = self._clean_name(name)
        caller    = self._addr()
        new_owner = new_owner.lower().strip()
        records   = self._records()
        if key not in records:
            raise Exception(f"{key}.gen is not registered")
        if records[key]["owner"] != caller:
            raise Exception("You don't own this name")
        if not new_owner.startswith("0x") or len(new_owner) != 42:
            raise Exception("Invalid new owner address")
        records[key]["owner"] = new_owner
        self._save_records(records)
        # Update primary reverse mapping
        reverse = self._reverse()
        if reverse.get(caller) == key:
            del reverse[caller]
        if new_owner not in reverse:
            reverse[new_owner] = key
        self._save_reverse(reverse)

    @gl.public.write
    def set_primary(self, name: str):
        """Set which .gen name is your primary (shown by default)."""
        key     = self._clean_name(name)
        caller  = self._addr()
        records = self._records()
        if key not in records:
            raise Exception(f"{key}.gen is not registered")
        if records[key]["owner"] != caller:
            raise Exception("You don't own this name")
        reverse         = self._reverse()
        reverse[caller] = key
        self._save_reverse(reverse)

    @gl.public.write
    def release(self, name: str):
        """Release a .gen name back to the pool."""
        key     = self._clean_name(name)
        caller  = self._addr()
        records = self._records()
        if key not in records:
            raise Exception(f"{key}.gen is not registered")
        if records[key]["owner"] != caller:
            raise Exception("You don't own this name")
        del records[key]
        self._save_records(records)
        reverse = self._reverse()
        if reverse.get(caller) == key:
            del reverse[caller]
        self._save_reverse(reverse)
