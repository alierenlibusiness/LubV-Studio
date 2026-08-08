# Getting started

[← Back to index](README.md)

## 1. Install

### Prebuilt application

Download the build for your platform from [Releases](../../releases).
No Python needed, nothing to configure.

- Windows: `LUBV Studio.exe`, a single file.
- macOS: `LUBV Studio.app`, drag it into Applications.

### From source

```bash
git clone https://github.com/alierenlibusiness/LubV-Studio.git
cd LubV-Studio
pip install -r requirements.txt
python -m lubv_studio
```

Python 3.10 or newer, on Windows or macOS. On macOS use `./run.sh` instead of
the commands above if you prefer a single step.

## 2. Get an API key

Sign up at [platform.deepseek.com](https://platform.deepseek.com), create a key
and top up a small amount of credit. A dollar goes a very long way here; typical
requests cost a fraction of a cent.

## 3. Point it at a project

On first launch the app asks for a folder. Pick the project you want to work on.

This folder is the boundary. The agent can read and write anything inside it and
nothing outside it. To switch later, press `Ctrl+O` or use the folder icon in
the Files panel header.

## 4. Enter the key

Open **Settings** (gear icon, bottom of the left rail), paste the key, then
press **Test connection**. It confirms the key and shows your remaining balance.

While you are there, pick a model:

- **V4 Flash:** the default. Fast, cheap, 1M token context. Right for almost
  everything.
- **V4 Pro:** noticeably stronger on hard architectural work. Roughly three
  times the price.

## 5. Write the brain

Open the **Brain** panel (the spark icon). This text box is the entire system
prompt. Replace it with whatever you want the agent to be, then press **Save**.

See [Writing the brain](writing-the-brain.md) for what tends to work.

## 6. Give it something to do

Type into the chat on the right and press Enter. Some first tasks that show what
it does:

```
look through this project and explain what it does
```

```
read main.py and add proper error handling to the file loading
```

```
this crashes with "KeyError: config", find out why and fix it
```

```
check what the latest version of requests is and update requirements.txt
```

```
commit everything with a sensible message and push it
```

## What you will see

The agent works in visible steps. Each tool call becomes a card showing what it
did, how long it took, and its output when you expand it. If you are in
**Approve** mode, a dialog appears before any write with a line by line diff.
If you are in **Auto** mode, it just goes.

When it finishes, the status bar shows what the turn cost.

## Next

- [Writing the brain](writing-the-brain.md)
- [Tool reference](tool-reference.md)
- [Cost and models](cost-and-models.md)
