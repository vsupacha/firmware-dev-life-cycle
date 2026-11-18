# Security

## Reporting a problem

Please report security problems privately through GitHub: the repository's **Security** tab >
**Report a vulnerability**. Do not open a public issue for them.

Please report, for example:

- a way to make the Auto page flash a board or delete an app folder without the Approve click, or with an
  approval given for a different image;
- a stage shown as passed although its script failed or printed no gate line;
- personal or machine data that ends up in a published file.

## What this project does on your PC

- The UI listens on `127.0.0.1` only. It starts the scripts of the skill repositories that sit next to it
  (`providers/*.json` name the commands); it installs nothing.
- The delete stage removes one app folder, only after approval, only a direct child of your apps workspace
  that holds the skill's marker file.
- Run records and logs are stored in `~/.firmware-dev-life-cycle/`.
- Local LLM endpoints and the background agent are optional and are described in `docs/`.
