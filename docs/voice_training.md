# Local conversation training

`/train chat` prepares an encrypted, user-approved conversation dataset for a future Solace voice profile. This
first stage does not change Solace's replies yet.

## Import workflow

1. Export a WhatsApp chat without media, or prepare a UTF-8 `.txt` file containing `Speaker: message` lines.
2. Run `/train chat` and enter the file path or filename, or use `/train chat <file.txt>`.
3. Choose the one participant whose writing style Solace may learn. Messages from all other participants are
   discarded after parsing and are never written to the training directory.
4. Review messages flagged for identifiers, financial/medical/sexual/violent content, secrets, or offensive
   language. Choose `remove`, `redacted`, `keep`, `edit`, or `cancel` for each flagged message.
5. Review the aggregate summary and explicitly approve encrypted storage.

The source transcript is read locally, is never modified, and is never copied into Solace. Scripted command mode
refuses imports because it cannot provide human review.

## Privacy boundary

Pattern matching can identify common emails, URLs, phone/account-like numbers and selected sensitive terms. It
cannot guarantee complete anonymisation: nicknames, names, indirect personal stories, unusual addresses and
context-specific offensive language may not be recognised. The person importing the transcript remains responsible
for final approval and should use `edit` or `remove` whenever a message should not be retained.

Approved message text is encrypted with Solace's existing local cipher and saved at:

```text
~/.solace/training/voice/<profile>/approved_examples.enc
```

An unencrypted `import_report.json` stores only the profile label, aggregate counts and creation time. The profile
label itself is therefore not secret. These files live outside the Git checkout and are preserved by `solace update`.
An existing approved profile is never overwritten by another import.
