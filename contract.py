# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
import json
from genlayer import *


class DotGen(gl.Contract):
    """
    dotgen — community .gen name registry on GenLayer Bradbury.
    AI validates every name registration — blocks impersonation
    and inappropriate names before they land on-chain.
    Upgraded: TreeMap storage + DynArray name index.
    """

    records: TreeMap[str, str]  # name_key -> json({owner, address, url, avatar, bio})
    reverse: TreeMap[str, str]  # address  -> primary_name
    names:   DynArray[str]      # all registered name keys (for iteration)
    owner:   str

    MIN_LEN = 3
    MAX_LEN = 32

    def __init__(self):
        self.owner = str(gl.message.sender_address).lower().strip()
        root = gl.storage.Root.get()
        root.upgraders.get().append(gl.message.sender_address)

    # ── Helpers ──────────────────────────────────────────────
    def _addr(self) -> str: return str(gl.message.sender_address).lower().strip()

    def _clean_name(self, name: str) -> str:
        return name.strip().lower().replace(".gen", "").replace(" ", "")

    def _get_record(self, key: str) -> dict:
        raw = self.records.get(key, None)
        if raw is None:
            return {}
        return json.loads(raw)

    def _save_record(self, key: str, r: dict):
        self.records[key] = json.dumps(r)

    def _del_record(self, key: str):
        try:
            del self.records[key]
        except Exception:
            pass

    # ── Views ─────────────────────────────────────────────────
    @gl.public.view
    def get_record(self, name: str) -> str:
        key = self._clean_name(name)
        raw = self.records.get(key, None)
        if raw is None:
            return "NOT_FOUND"
        return raw

    @gl.public.view
    def is_available(self, name: str) -> str:
        key = self._clean_name(name)
        if len(key) < self.MIN_LEN or len(key) > self.MAX_LEN:
            return "INVALID"
        for ch in key:
            if not (ch.isalnum() or ch == "-" or ch == "_"):
                return "INVALID"
        if self.records.get(key, None) is not None:
            return "TAKEN"
        return "AVAILABLE"

    @gl.public.view
    def get_name_by_address(self, address: str) -> str:
        return self.reverse.get(address.lower().strip(), "")

    @gl.public.view
    def get_all_names(self) -> str:
        result = []
        for i in range(len(self.names)):
            key = self.names[i]
            raw = self.records.get(key, None)
            if raw is None:
                continue  # released name — skip
            r = json.loads(raw)
            result.append({
                "name":    key,
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

    @gl.public.view
    def get_name_count(self) -> str:
        return str(len(self.names))

    # ── Writes ────────────────────────────────────────────────

    @gl.public.write
    def upgrade(self, new_code: bytes) -> None:
        """Push a new version without changing the contract address. Deployer only."""
        root = gl.storage.Root.get()
        code = root.code.get()
        code.truncate()
        code.extend(new_code)

    @gl.public.write
    def register(self, name: str, address: str,
                 url: str, avatar: str, bio: str):
        """
        Register a .gen name. AI validates the name is appropriate
        and not impersonating a known person or brand.
        """
        key    = self._clean_name(name)
        caller = self._addr()

        if len(key) < self.MIN_LEN:
            raise Exception(f"Name too short (minimum {self.MIN_LEN} characters)")
        if len(key) > self.MAX_LEN:
            raise Exception(f"Name too long (maximum {self.MAX_LEN} characters)")
        for ch in key:
            if not (ch.isalnum() or ch == "-" or ch == "_"):
                raise Exception("Letters, numbers, hyphens, and underscores only")
        if self.records.get(key, None) is not None:
            raise Exception(f"{key}.gen is already registered")

        target_addr = address.strip() if address.strip() else caller

        # ── AI validation ─────────────────────────────────────
        def validate_name():
            prompt = (
                "You are a domain name registrar for the GenLayer blockchain (.gen domains).\n"
                "Evaluate if this name is appropriate to register:\n\n"
                "NAME: " + key + ".gen\n"
                "REGISTRANT: " + caller + "\n\n"
                "REJECT if the name:\n"
                "- Is a well-known person's name (vitalik, satoshi, elonmusk, etc.)\n"
                "- Impersonates a major brand or protocol "
                "  (ethereum, bitcoin, genlayer, uniswap, metamask, etc.)\n"
                "- Contains hate speech, slurs, or explicit content\n"
                "- Is a government entity or official institution\n\n"
                "APPROVE if the name:\n"
                "- Is a creative handle, nickname, or brand\n"
                "- References a concept, animal, object, or abstract term\n"
                "- Could plausibly be a personal username\n\n"
                "Reply with ONLY:\n"
                "APPROVED\n"
                "or\n"
                "REJECTED: <one short reason>"
            )
            return gl.nondet.exec_prompt(prompt)

        verdict = str(gl.eq_principle.prompt_non_comparative(
            validate_name,
            task="Decide if a .gen domain name is appropriate to register.",
            criteria=(
                "Validate format only - do NOT re-evaluate the decision. "
                "Accept if: (1) reply starts with 'APPROVED' or 'REJECTED:', "
                "(2) if REJECTED, a short reason follows. "
                "Do not override the leader's judgment."
            ),
        )).strip()

        if verdict.upper().startswith("REJECTED"):
            reason = verdict[9:].strip(": ").strip() or "Name not allowed"
            raise Exception(f"Registration rejected: {reason}")

        # ── Store ─────────────────────────────────────────────
        self._save_record(key, {
            "name":    key,
            "owner":   caller,
            "address": target_addr,
            "url":     url.strip(),
            "avatar":  avatar.strip(),
            "bio":     bio.strip()[:200],
        })
        self.names.append(key)

        # Set as primary if none exists
        if self.reverse.get(caller, None) is None:
            self.reverse[caller] = key

    @gl.public.write
    def update_record(self, name: str, url: str, avatar: str, bio: str):
        """Update URL, avatar, and bio for a .gen name you own."""
        key    = self._clean_name(name)
        caller = self._addr()
        r      = self._get_record(key)
        if not r:
            raise Exception(f"{key}.gen is not registered")
        if r["owner"] != caller:
            raise Exception("You don't own this name")
        r["url"]    = url.strip()
        r["avatar"] = avatar.strip()
        r["bio"]    = bio.strip()[:200]
        self._save_record(key, r)

    @gl.public.write
    def transfer(self, name: str, new_owner: str):
        """Transfer a .gen name to a new address."""
        key       = self._clean_name(name)
        caller    = self._addr()
        new_owner = new_owner.lower().strip()
        r         = self._get_record(key)
        if not r:
            raise Exception(f"{key}.gen is not registered")
        if r["owner"] != caller:
            raise Exception("You don't own this name")
        if not new_owner.startswith("0x") or len(new_owner) != 42:
            raise Exception("Invalid new owner address")
        r["owner"] = new_owner
        self._save_record(key, r)
        # Update reverse mapping
        if self.reverse.get(caller, "") == key:
            try: del self.reverse[caller]
            except: pass
        if self.reverse.get(new_owner, None) is None:
            self.reverse[new_owner] = key

    @gl.public.write
    def set_primary(self, name: str):
        """Set which .gen name is your primary."""
        key    = self._clean_name(name)
        caller = self._addr()
        r      = self._get_record(key)
        if not r:
            raise Exception(f"{key}.gen is not registered")
        if r["owner"] != caller:
            raise Exception("You don't own this name")
        self.reverse[caller] = key

    @gl.public.write
    def release(self, name: str):
        """Release a .gen name back to the pool."""
        key    = self._clean_name(name)
        caller = self._addr()
        r      = self._get_record(key)
        if not r:
            raise Exception(f"{key}.gen is not registered")
        if r["owner"] != caller:
            raise Exception("You don't own this name")
        self._del_record(key)
        # name stays in DynArray but records lookup returns None (filtered in get_all_names)
        if self.reverse.get(caller, "") == key:
            try: del self.reverse[caller]
            except: pass
