# Betslip Simulator

Multi-sportsbook betslip simulator for validating parlay construction across FanDuel, DraftKings, and Bet365.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Credentials

The simulator requires credentials for each sportsbook you want to test. You can set them up in two ways:

#### Option A: Using .env file (Recommended)

1. Run the setup script:
```bash
python setup_env.py
```

2. Edit the `.env` file with your actual credentials:
```bash
# FanDuel Credentials
FANDUEL_EMAIL=your_actual_email@example.com
FANDUEL_PASSWORD=your_actual_password

# DraftKings Credentials
DRAFTKINGS_EMAIL=your_actual_email@example.com
DRAFTKINGS_PASSWORD=your_actual_password

# Bet365 Credentials
BET365_USERNAME=your_actual_username
BET365_PASSWORD=your_actual_password
```

#### Option B: Environment Variables

Set the credentials directly in your environment:

```bash
export FANDUEL_EMAIL="your_email@example.com"
export FANDUEL_PASSWORD="your_password"
export DRAFTKINGS_EMAIL="your_email@example.com"
export DRAFTKINGS_PASSWORD="your_password"
export BET365_USERNAME="your_username"
export BET365_PASSWORD="your_password"
```

### 3. MFA/2FA Authentication

Sportsbooks typically require MFA (Multi-Factor Authentication). The simulator supports several approaches:

#### Option A: Interactive MFA Prompts
```bash
python scripts/betslip_simulator.py --mfa-prompt --headed
```
This will prompt you for MFA codes as needed during login.

#### Option B: Command Line MFA Code
```bash
python scripts/betslip_simulator.py --mfa-code 123456 --headed
```
Provide the MFA code directly via command line.

#### Option C: Environment Variables
Add MFA codes to your `.env` file:
```bash
FANDUEL_MFA_CODE=your_fanduel_mfa_code
DRAFTKINGS_MFA_CODE=your_draftkings_mfa_code
BET365_MFA_CODE=your_bet365_mfa_code
```

#### Option D: Manual Login (Fallback)
If you prefer not to store credentials or MFA codes:

```bash
python scripts/betslip_simulator.py --manual-login --headed
```

This will pause after navigating to each login page, allowing you to complete MFA/captcha challenges manually.

## Usage

### Basic Usage

```bash
# Test all books with a parlay
python scripts/betslip_simulator.py \
    --sport-key basketball_nba \
    --game-id 12345 \
    --legs-json data/parlay_legs.json

# Test specific books only
python scripts/betslip_simulator.py \
    --books fanduel draftkings \
    --sport-key basketball_nba \
    --game-id 12345 \
    --legs-json data/parlay_legs.json
```

### Advanced Options

```bash
# Dry run (validate selectors only)
python scripts/betslip_simulator.py \
    --books fanduel \
    --sport-key basketball_nba \
    --game-id 12345 \
    --legs-json data/parlay_legs.json \
    --dry-run

# With MFA and video recording
python scripts/betslip_simulator.py \
    --books fanduel draftkings bet365 \
    --sport-key basketball_nba \
    --game-id 12345 \
    --legs-json data/parlay_legs.json \
    --headed \
    --mfa-prompt \
    --video

# With specific MFA code
python scripts/betslip_simulator.py \
    --books fanduel \
    --sport-key basketball_nba \
    --game-id 12345 \
    --legs-json data/parlay_legs.json \
    --mfa-code 123456 \
    --headed

# Clear stored browser states
python scripts/betslip_simulator.py --logout
```

## Input Format

Create a JSON file with your parlay legs:

```json
[
  {
    "market": "h2h",
    "selection_name": "Lakers"
  },
  {
    "market": "spreads",
    "selection_name": "Warriors +2.5",
    "line": 2.5
  },
  {
    "market": "totals",
    "selection_name": "Over 220.5",
    "line": 220.5
  }
]
```

## Output

The simulator generates:

- **Console Summary**: Pass/fail table for each book
- **Screenshots**: Per-step captures for debugging
- **Videos**: Full session recordings (if --video flag used)
- **JSON Summary**: Machine-readable results with timestamps
- **Browser States**: Saved login sessions for faster subsequent runs

## Exit Codes

- `0`: All books validate as VALID
- `1`: Any book returns INVALID (betting rules violation)
- `2`: Fatal setup errors (missing credentials, bad legs file)

## Security Notes

- Never commit `.env` files to version control
- Credentials are automatically redacted from logs
- Browser state files are stored locally for convenience
- Use `--logout` to clear stored states

## Troubleshooting

### Missing Credentials
```
❌ Missing credentials for the following books:
   fanduel: FANDUEL_EMAIL, FANDUEL_PASSWORD
```

**Solution**: Set up your `.env` file or use `--manual-login`

### Login Failures
```
FanDuel login failed
```

**Solutions**:
1. Check your credentials are correct
2. Use `--mfa-prompt` for interactive MFA handling
3. Use `--mfa-code` to provide MFA code directly
4. Use `--manual-login` to handle everything manually
5. Clear stored states with `--logout`

### Navigation Issues
```
FanDuel navigation error
```

**Solutions**:
1. Check if the game is available on the sportsbook
2. Verify team names match exactly
3. Use `--headed` to see what's happening

### Selector Issues
```
Could not find selection for leg
```

**Solutions**:
1. Use `--dry-run` to validate selectors
2. Check if the market/line is available
3. Verify the selection name matches exactly
