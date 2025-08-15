#!/usr/bin/env python3
"""
Multi-sportsbook betslip simulator for validating parlay construction.

Validates parlay legs across FanDuel, DraftKings, and Bet365 by attempting to
construct betslips and detecting any sportsbook errors that would invalidate them.
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If python-dotenv is not installed, try to load .env manually
    env_path = Path('.env')
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SelectorRegistry:
    """Registry of selectors for different sportsbooks."""
    
    FANDUEL = {
        'login_url': 'https://sportsbook.fanduel.com/login',
        'username_input': '[data-testid="email-input"]',
        'password_input': '[data-testid="password-input"]',
        'login_button': '[data-testid="login-button"]',
        'account_avatar': '[data-testid="account-menu-button"]',
        'search_box': '[data-testid="search-input"]',
        'betslip_panel': '[data-testid="betslip"]',
        'betslip_count': '[data-testid="betslip-count"]',
        'error_banner': '[data-testid="error-message"], .error-banner, .alert-error',
        'team_button': '[data-testid="team-button"]',
        'spread_button': '[data-testid="spread-button"]',
        'total_button': '[data-testid="total-button"]',
        'clear_betslip': '[data-testid="clear-betslip"]'
    }
    
    DRAFTKINGS = {
        'login_url': 'https://sportsbook.draftkings.com/login',
        'username_input': '#username',
        'password_input': '#password',
        'login_button': '[data-testid="login-submit"]',
        'account_avatar': '[data-testid="user-menu"]',
        'search_box': '[data-testid="search-input"]',
        'betslip_panel': '[data-testid="betslip"]',
        'betslip_count': '[data-testid="betslip-count"]',
        'error_banner': '.error-message, .alert-error, [data-testid="error-banner"]',
        'team_button': '[data-testid="team-button"]',
        'spread_button': '[data-testid="spread-button"]',
        'total_button': '[data-testid="total-button"]',
        'clear_betslip': '[data-testid="clear-betslip"]'
    }
    
    BET365 = {
        'login_url': 'https://www.bet365.com/login',
        'username_input': '#username',
        'password_input': '#password',
        'login_button': '.hm-MainHeaderMembersWide_Login',
        'account_avatar': '.hm-MainHeaderMembersWide_UserName',
        'search_box': '.search-input',
        'betslip_panel': '.betslip',
        'betslip_count': '.betslip-count',
        'error_banner': '.error-message, .alert-error',
        'team_button': '.team-button',
        'spread_button': '.spread-button',
        'total_button': '.total-button',
        'clear_betslip': '.clear-betslip'
    }


class ErrorRegistry:
    """Registry of error patterns for different sportsbooks."""
    
    FANDUEL = [
        "Same Game Parlay not allowed",
        "Selection cannot be combined",
        "ineligible combination",
        "invalid parlay",
        "betting rules violation"
    ]
    
    DRAFTKINGS = [
        "Same Game Parlay not allowed",
        "Selection cannot be combined",
        "ineligible combination",
        "invalid parlay",
        "betting rules violation"
    ]
    
    BET365 = [
        "Same Game Parlay not allowed",
        "Selection cannot be combined",
        "ineligible combination",
        "invalid parlay",
        "betting rules violation"
    ]


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Multi-sportsbook betslip simulator")
    
    parser.add_argument("--books", nargs="+", 
                       choices=["fanduel", "draftkings", "bet365"],
                       default=["fanduel", "draftkings", "bet365"],
                       help="Sportsbooks to test (default: all)")
    parser.add_argument("--sport-key", required=True,
                       help="Sport key (e.g., basketball_nba)")
    parser.add_argument("--game-id", required=True,
                       help="Internal game ID")
    parser.add_argument("--home", help="Home team name (fallback)")
    parser.add_argument("--away", help="Away team name (fallback)")
    parser.add_argument("--legs-json", required=True, type=Path,
                       help="Path to parlay legs JSON file")
    parser.add_argument("--region", default="us",
                       help="Region (default: us)")
    parser.add_argument("--headed", action="store_true",
                       help="Run in headed mode")
    parser.add_argument("--manual-login", action="store_true",
                       help="Pause for manual login")
    parser.add_argument("--mfa-code", type=str,
                       help="MFA/2FA code for authentication")
    parser.add_argument("--mfa-prompt", action="store_true",
                       help="Prompt for MFA code interactively")
    parser.add_argument("--timeout-sec", type=int, default=40,
                       help="Timeout per step (default: 40)")
    parser.add_argument("--slowmo-ms", type=int, default=0,
                       help="Slow motion for debugging (default: 0)")
    parser.add_argument("--screenshot-dir", type=Path,
                       default=Path(f"artifacts/betslip_simulator/{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
                       help="Screenshot directory")
    parser.add_argument("--video", action="store_true",
                       help="Record video")
    parser.add_argument("--max-retries", type=int, default=1,
                       help="Max retries per action (default: 1)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Only resolve selectors, don't click")
    parser.add_argument("--logout", action="store_true",
                       help="Clear storage state")
    
    return parser.parse_args()


def load_legs(legs_path: Path) -> List[Dict[str, Any]]:
    """Load and validate parlay legs from JSON file."""
    try:
        with open(legs_path, 'r') as f:
            legs = json.load(f)
        
        if not isinstance(legs, list):
            raise ValueError("Legs must be a list")
        
        # Validate each leg
        for i, leg in enumerate(legs):
            required_fields = ['market', 'selection_name']
            for field in required_fields:
                if field not in leg:
                    raise ValueError(f"Leg {i} missing required field: {field}")
            
            # Validate market type
            valid_markets = ['h2h', 'spreads', 'totals', 'player_points']
            if leg['market'] not in valid_markets:
                raise ValueError(f"Leg {i} invalid market: {leg['market']}")
            
            # Validate line for spreads/totals
            if leg['market'] in ['spreads', 'totals'] and 'line' not in leg:
                raise ValueError(f"Leg {i} missing line for {leg['market']} market")
        
        logger.info(f"Loaded {len(legs)} legs from {legs_path}")
        return legs
        
    except Exception as e:
        logger.error(f"Failed to load legs: {e}")
        sys.exit(2)


def redact(text: str) -> str:
    """Redact sensitive information from logs."""
    if not text:
        return text
    
    # Redact email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
    
    # Redact passwords (simple heuristic)
    text = re.sub(r'password["\']?\s*[:=]\s*["\']?[^"\s]+["\']?', 'password="[REDACTED]"', text, flags=re.IGNORECASE)
    
    return text


def ensure_dir(path: Path) -> None:
    """Ensure directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def screenshot(page: Page, path: Path, name: str) -> None:
    """Take screenshot and save to path."""
    ensure_dir(path)
    screenshot_path = path / f"{name}.png"
    page.screenshot(path=str(screenshot_path))
    logger.debug(f"Screenshot saved: {screenshot_path}")


def save_state(context: BrowserContext, book: str) -> None:
    """Save browser state for future login."""
    state_path = Path(f"artifacts/state_{book}.json")
    ensure_dir(state_path.parent)
    context.storage_state(path=str(state_path))
    logger.info(f"Saved state for {book}")


def load_state(context: BrowserContext, book: str) -> bool:
    """Load browser state if available."""
    state_path = Path(f"artifacts/state_{book}.json")
    if state_path.exists():
        context.storage_state(path=str(state_path))
        logger.info(f"Loaded state for {book}")
        return True
    return False


def clear_state(book: str) -> None:
    """Clear stored state for a book."""
    state_path = Path(f"artifacts/state_{book}.json")
    if state_path.exists():
        state_path.unlink()
        logger.info(f"Cleared state for {book}")


def validate_credentials(books: List[str]) -> Dict[str, bool]:
    """Validate that required credentials are available for each book."""
    credentials_status = {}
    
    for book in books:
        if book == 'fanduel':
            email = os.getenv('FANDUEL_EMAIL')
            password = os.getenv('FANDUEL_PASSWORD')
            credentials_status[book] = bool(email and password)
        elif book == 'draftkings':
            email = os.getenv('DRAFTKINGS_EMAIL')
            password = os.getenv('DRAFTKINGS_PASSWORD')
            credentials_status[book] = bool(email and password)
        elif book == 'bet365':
            username = os.getenv('BET365_USERNAME')
            password = os.getenv('BET365_PASSWORD')
            credentials_status[book] = bool(username and password)
        else:
            credentials_status[book] = False
    
    return credentials_status


def prompt_for_mfa_code(book: str) -> str:
    """Prompt user for MFA code interactively."""
    print(f"\n🔐 MFA Required for {book.upper()}")
    print("Please check your:")
    print("  • Email for verification code")
    print("  • SMS for text message code")
    print("  • Authenticator app (Google Authenticator, Authy, etc.)")
    print("  • Any other 2FA method you have enabled")
    print()
    
    while True:
        mfa_code = input(f"Enter MFA code for {book}: ").strip()
        if mfa_code:
            return mfa_code
        else:
            print("❌ MFA code cannot be empty. Please try again.")


def handle_mfa(page: Page, args: argparse.Namespace, book: str) -> bool:
    """Handle MFA authentication for a specific book."""
    # Get MFA code from various sources
    mfa_code = None
    if args.mfa_code:
        mfa_code = args.mfa_code
    elif hasattr(args, f'{book}_mfa_code'):
        mfa_code = getattr(args, f'{book}_mfa_code')
    elif os.getenv(f'{book.upper()}_MFA_CODE'):
        mfa_code = os.getenv(f'{book.upper()}_MFA_CODE')
    
    if not mfa_code:
        return False
    
    # Try to find MFA input field
    mfa_selectors = [
        '[data-testid="mfa-input"]',
        '[data-testid="verification-code"]',
        'input[name="code"]',
        'input[placeholder*="code"]',
        'input[placeholder*="Code"]',
        '#mfa-code',
        '#verification-code',
        'input[type="text"]',  # Generic fallback
        'input[autocomplete="one-time-code"]'
    ]
    
    mfa_input = None
    for selector in mfa_selectors:
        mfa_input = page.query_selector(selector)
        if mfa_input:
            break
    
    if mfa_input:
        logger.info(f"MFA input field found for {book}, entering code...")
        mfa_input.fill(mfa_code)
        
        # Try to find submit button
        submit_selectors = [
            '[data-testid="mfa-submit"]',
            '[data-testid="verify-button"]',
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Verify")',
            'button:has-text("Submit")',
            'button:has-text("Continue")'
        ]
        
        for selector in submit_selectors:
            submit_btn = page.query_selector(selector)
            if submit_btn:
                submit_btn.click()
                page.wait_for_load_state('networkidle')
                return True
        
        # If no submit button found, try pressing Enter
        mfa_input.press('Enter')
        page.wait_for_load_state('networkidle')
        return True
    else:
        logger.warning(f"MFA code provided for {book} but no MFA input field found")
        return False


def wait_for_text(page: Page, text: str, timeout: int = 10000) -> bool:
    """Wait for text to appear on page."""
    try:
        page.wait_for_function(f'document.body.textContent.includes("{text}")', timeout=timeout)
        return True
    except:
        return False


def find_line_with_tolerance(page: Page, target_line: float, tolerance: float = 0.25) -> Optional[str]:
    """Find selection with line within tolerance."""
    # This is a simplified implementation - in practice, you'd need more sophisticated
    # text parsing based on the specific sportsbook's DOM structure
    try:
        elements = page.query_selector_all('[data-testid*="line"], [data-testid*="spread"], [data-testid*="total"]')
        for element in elements:
            text = element.text_content()
            if text:
                # Extract numeric value from text
                match = re.search(r'[+-]?\d+\.?\d*', text)
                if match:
                    line_value = float(match.group())
                    if abs(line_value - target_line) <= tolerance:
                        return text
        return None
    except:
        return None


def login_fanduel(page: Page, args: argparse.Namespace) -> bool:
    """Login to FanDuel."""
    try:
        logger.info("Logging into FanDuel...")
        
        # Navigate to login page
        page.goto(SelectorRegistry.FANDUEL['login_url'])
        page.wait_for_load_state('networkidle')
        
        if args.manual_login:
            logger.info("Manual login mode - complete MFA/captcha in browser")
            input("Press ENTER after completing login and MFA: ")
            return True
        
        # Fill credentials
        email = os.getenv('FANDUEL_EMAIL')
        password = os.getenv('FANDUEL_PASSWORD')
        
        if not email or not password:
            logger.error("FanDuel credentials not found in environment")
            return False
        
        page.fill(SelectorRegistry.FANDUEL['username_input'], email)
        page.fill(SelectorRegistry.FANDUEL['password_input'], password)
        
        # Submit login
        page.click(SelectorRegistry.FANDUEL['login_button'])
        page.wait_for_load_state('networkidle')
        
        # Handle MFA if present
        handle_mfa(page, args, 'fanduel')
        
        # Check for successful login
        try:
            page.wait_for_selector(SelectorRegistry.FANDUEL['account_avatar'], timeout=15000)
            logger.info("FanDuel login successful")
            return True
        except:
            # Check if we're on an MFA page
            if page.query_selector('[data-testid="mfa-input"]') or page.query_selector('input[name="code"]'):
                logger.warning("MFA required but no code provided. Use --mfa-code or --manual-login")
                if not args.headed:
                    logger.info("Consider using --headed flag to see the MFA prompt")
                return False
            else:
                logger.error("FanDuel login failed")
                return False
            
    except Exception as e:
        logger.error(f"FanDuel login error: {e}")
        return False


def login_draftkings(page: Page, args: argparse.Namespace) -> bool:
    """Login to DraftKings."""
    try:
        logger.info("Logging into DraftKings...")
        
        # Navigate to login page
        page.goto(SelectorRegistry.DRAFTKINGS['login_url'])
        page.wait_for_load_state('networkidle')
        
        if args.manual_login:
            logger.info("Manual login mode - complete MFA/captcha in browser")
            input("Press ENTER after completing login and MFA: ")
            return True
        
        # Fill credentials
        email = os.getenv('DRAFTKINGS_EMAIL')
        password = os.getenv('DRAFTKINGS_PASSWORD')
        
        if not email or not password:
            logger.error("DraftKings credentials not found in environment")
            return False
        
        page.fill(SelectorRegistry.DRAFTKINGS['username_input'], email)
        page.fill(SelectorRegistry.DRAFTKINGS['password_input'], password)
        
        # Submit login
        page.click(SelectorRegistry.DRAFTKINGS['login_button'])
        page.wait_for_load_state('networkidle')
        
        # Handle MFA if present
        handle_mfa(page, args, 'draftkings')
        
        # Check for successful login
        try:
            page.wait_for_selector(SelectorRegistry.DRAFTKINGS['account_avatar'], timeout=15000)
            logger.info("DraftKings login successful")
            return True
        except:
            # Check if we're on an MFA page
            if page.query_selector('[data-testid="mfa-input"]') or page.query_selector('input[name="code"]'):
                logger.warning("MFA required but no code provided. Use --mfa-code or --manual-login")
                if not args.headed:
                    logger.info("Consider using --headed flag to see the MFA prompt")
                return False
            else:
                logger.error("DraftKings login failed")
                return False
            
    except Exception as e:
        logger.error(f"DraftKings login error: {e}")
        return False


def login_bet365(page: Page, args: argparse.Namespace) -> bool:
    """Login to Bet365."""
    try:
        logger.info("Logging into Bet365...")
        
        # Navigate to login page
        page.goto(SelectorRegistry.BET365['login_url'])
        page.wait_for_load_state('networkidle')
        
        if args.manual_login:
            logger.info("Manual login mode - complete MFA/captcha in browser")
            input("Press ENTER after completing login and MFA: ")
            return True
        
        # Fill credentials
        username = os.getenv('BET365_USERNAME')
        password = os.getenv('BET365_PASSWORD')
        
        if not username or not password:
            logger.error("Bet365 credentials not found in environment")
            return False
        
        page.fill(SelectorRegistry.BET365['username_input'], username)
        page.fill(SelectorRegistry.BET365['password_input'], password)
        
        # Submit login
        page.click(SelectorRegistry.BET365['login_button'])
        page.wait_for_load_state('networkidle')
        
        # Handle MFA if present
        handle_mfa(page, args, 'bet365')
        
        # Check for successful login
        try:
            page.wait_for_selector(SelectorRegistry.BET365['account_avatar'], timeout=15000)
            logger.info("Bet365 login successful")
            return True
        except:
            # Check if we're on an MFA page
            if page.query_selector('[data-testid="mfa-input"]') or page.query_selector('input[name="code"]'):
                logger.warning("MFA required but no code provided. Use --mfa-code or --manual-login")
                if not args.headed:
                    logger.info("Consider using --headed flag to see the MFA prompt")
                return False
            else:
                logger.error("Bet365 login failed")
                return False
            
    except Exception as e:
        logger.error(f"Bet365 login error: {e}")
        return False


def navigate_to_game_fanduel(page: Page, args: argparse.Namespace) -> bool:
    """Navigate to target game on FanDuel."""
    try:
        logger.info("Navigating to game on FanDuel...")
        
        # Navigate to NBA section
        page.goto("https://sportsbook.fanduel.com/basketball/nba")
        page.wait_for_load_state('networkidle')
        
        # Try to find the specific game
        if args.home and args.away:
            search_text = f"{args.home} vs {args.away}"
            if page.query_selector(SelectorRegistry.FANDUEL['search_box']):
                page.fill(SelectorRegistry.FANDUEL['search_box'], search_text)
                page.keyboard.press('Enter')
                page.wait_for_load_state('networkidle')
        
        screenshot(page, args.screenshot_dir / "fanduel", "01_game_page")
        return True
        
    except Exception as e:
        logger.error(f"FanDuel navigation error: {e}")
        return False


def navigate_to_game_draftkings(page: Page, args: argparse.Namespace) -> bool:
    """Navigate to target game on DraftKings."""
    try:
        logger.info("Navigating to game on DraftKings...")
        
        # Navigate to NBA section
        page.goto("https://sportsbook.draftkings.com/basketball/nba")
        page.wait_for_load_state('networkidle')
        
        # Try to find the specific game
        if args.home and args.away:
            search_text = f"{args.home} vs {args.away}"
            if page.query_selector(SelectorRegistry.DRAFTKINGS['search_box']):
                page.fill(SelectorRegistry.DRAFTKINGS['search_box'], search_text)
                page.keyboard.press('Enter')
                page.wait_for_load_state('networkidle')
        
        screenshot(page, args.screenshot_dir / "draftkings", "01_game_page")
        return True
        
    except Exception as e:
        logger.error(f"DraftKings navigation error: {e}")
        return False


def navigate_to_game_bet365(page: Page, args: argparse.Namespace) -> bool:
    """Navigate to target game on Bet365."""
    try:
        logger.info("Navigating to game on Bet365...")
        
        # Navigate to NBA section
        page.goto("https://www.bet365.com/sport/basketball")
        page.wait_for_load_state('networkidle')
        
        # Try to find the specific game
        if args.home and args.away:
            search_text = f"{args.home} vs {args.away}"
            if page.query_selector(SelectorRegistry.BET365['search_box']):
                page.fill(SelectorRegistry.BET365['search_box'], search_text)
                page.keyboard.press('Enter')
                page.wait_for_load_state('networkidle')
        
        screenshot(page, args.screenshot_dir / "bet365", "01_game_page")
        return True
        
    except Exception as e:
        logger.error(f"Bet365 navigation error: {e}")
        return False


def add_leg_fanduel(page: Page, leg: Dict[str, Any], args: argparse.Namespace) -> bool:
    """Add a leg to FanDuel betslip."""
    try:
        logger.debug(f"Adding leg to FanDuel: {leg['selection_name']}")
        
        if args.dry_run:
            return True
        
        # Find and click the appropriate selection based on market
        if leg['market'] == 'h2h':
            # Look for team button
            team_name = leg['selection_name']
            selector = f'[data-testid*="{team_name.lower()}"]'
            element = page.query_selector(selector)
            if element:
                element.click()
                page.wait_for_timeout(1000)
                return True
        
        elif leg['market'] == 'spreads':
            # Look for spread with line
            line = leg.get('line')
            if line is not None:
                # Try to find spread button with line
                selector = f'[data-testid*="spread"][data-testid*="{line}"]'
                element = page.query_selector(selector)
                if element:
                    element.click()
                    page.wait_for_timeout(1000)
                    return True
        
        elif leg['market'] == 'totals':
            # Look for total with line
            line = leg.get('line')
            if line is not None:
                over_under = "over" if "over" in leg['selection_name'].lower() else "under"
                selector = f'[data-testid*="total"][data-testid*="{over_under}"][data-testid*="{line}"]'
                element = page.query_selector(selector)
                if element:
                    element.click()
                    page.wait_for_timeout(1000)
                    return True
        
        elif leg['market'] == 'player_points':
            raise NotImplementedError("Player points market not implemented for FanDuel")
        
        logger.warning(f"Could not find selection for leg: {leg}")
        return False
        
    except Exception as e:
        logger.error(f"FanDuel add leg error: {e}")
        return False


def add_leg_draftkings(page: Page, leg: Dict[str, Any], args: argparse.Namespace) -> bool:
    """Add a leg to DraftKings betslip."""
    try:
        logger.debug(f"Adding leg to DraftKings: {leg['selection_name']}")
        
        if args.dry_run:
            return True
        
        # Similar logic to FanDuel but with DraftKings selectors
        if leg['market'] == 'h2h':
            team_name = leg['selection_name']
            selector = f'[data-testid*="{team_name.lower()}"]'
            element = page.query_selector(selector)
            if element:
                element.click()
                page.wait_for_timeout(1000)
                return True
        
        elif leg['market'] == 'spreads':
            line = leg.get('line')
            if line is not None:
                selector = f'[data-testid*="spread"][data-testid*="{line}"]'
                element = page.query_selector(selector)
                if element:
                    element.click()
                    page.wait_for_timeout(1000)
                    return True
        
        elif leg['market'] == 'totals':
            line = leg.get('line')
            if line is not None:
                over_under = "over" if "over" in leg['selection_name'].lower() else "under"
                selector = f'[data-testid*="total"][data-testid*="{over_under}"][data-testid*="{line}"]'
                element = page.query_selector(selector)
                if element:
                    element.click()
                    page.wait_for_timeout(1000)
                    return True
        
        elif leg['market'] == 'player_points':
            raise NotImplementedError("Player points market not implemented for DraftKings")
        
        logger.warning(f"Could not find selection for leg: {leg}")
        return False
        
    except Exception as e:
        logger.error(f"DraftKings add leg error: {e}")
        return False


def add_leg_bet365(page: Page, leg: Dict[str, Any], args: argparse.Namespace) -> bool:
    """Add a leg to Bet365 betslip."""
    try:
        logger.debug(f"Adding leg to Bet365: {leg['selection_name']}")
        
        if args.dry_run:
            return True
        
        # Similar logic but with Bet365 selectors
        if leg['market'] == 'h2h':
            team_name = leg['selection_name']
            selector = f'.team-button[data-team*="{team_name.lower()}"]'
            element = page.query_selector(selector)
            if element:
                element.click()
                page.wait_for_timeout(1000)
                return True
        
        elif leg['market'] == 'spreads':
            line = leg.get('line')
            if line is not None:
                selector = f'.spread-button[data-line="{line}"]'
                element = page.query_selector(selector)
                if element:
                    element.click()
                    page.wait_for_timeout(1000)
                    return True
        
        elif leg['market'] == 'totals':
            line = leg.get('line')
            if line is not None:
                over_under = "over" if "over" in leg['selection_name'].lower() else "under"
                selector = f'.total-button[data-type="{over_under}"][data-line="{line}"]'
                element = page.query_selector(selector)
                if element:
                    element.click()
                    page.wait_for_timeout(1000)
                    return True
        
        elif leg['market'] == 'player_points':
            raise NotImplementedError("Player points market not implemented for Bet365")
        
        logger.warning(f"Could not find selection for leg: {leg}")
        return False
        
    except Exception as e:
        logger.error(f"Bet365 add leg error: {e}")
        return False


def validate_betslip_fanduel(page: Page, legs: List[Dict[str, Any]], args: argparse.Namespace) -> Dict[str, Any]:
    """Validate FanDuel betslip for errors."""
    try:
        logger.info("Validating FanDuel betslip...")
        
        # Open betslip if not already open
        betslip_selector = SelectorRegistry.FANDUEL['betslip_panel']
        if not page.query_selector(betslip_selector):
            # Try to find betslip toggle
            toggle = page.query_selector('[data-testid="betslip-toggle"]')
            if toggle:
                toggle.click()
                page.wait_for_timeout(1000)
        
        # Check for error banners
        errors = []
        error_selector = SelectorRegistry.FANDUEL['error_banner']
        error_elements = page.query_selector_all(error_selector)
        
        for element in error_elements:
            error_text = element.text_content()
            if error_text:
                errors.append({
                    'message': error_text,
                    'selector': error_selector,
                    'screenshot': 'error_banner.png'
                })
        
        # Check for specific error patterns
        page_text = page.content()
        for error_pattern in ErrorRegistry.FANDUEL:
            if error_pattern.lower() in page_text.lower():
                errors.append({
                    'message': error_pattern,
                    'selector': 'page_text',
                    'screenshot': 'error_pattern.png'
                })
        
        # Count legs in betslip
        betslip_count = 0
        count_selector = SelectorRegistry.FANDUEL['betslip_count']
        count_element = page.query_selector(count_selector)
        if count_element:
            count_text = count_element.text_content()
            try:
                betslip_count = int(count_text)
            except:
                pass
        
        status = "VALID" if not errors else "INVALID"
        
        return {
            'status': status,
            'legs_added': betslip_count,
            'legs_attempted': len(legs),
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"FanDuel validation error: {e}")
        return {
            'status': 'ERROR',
            'legs_added': 0,
            'legs_attempted': len(legs),
            'errors': [{'message': str(e), 'selector': 'exception', 'screenshot': 'error.png'}]
        }


def validate_betslip_draftkings(page: Page, legs: List[Dict[str, Any]], args: argparse.Namespace) -> Dict[str, Any]:
    """Validate DraftKings betslip for errors."""
    try:
        logger.info("Validating DraftKings betslip...")
        
        # Similar logic to FanDuel but with DraftKings selectors
        errors = []
        error_selector = SelectorRegistry.DRAFTKINGS['error_banner']
        error_elements = page.query_selector_all(error_selector)
        
        for element in error_elements:
            error_text = element.text_content()
            if error_text:
                errors.append({
                    'message': error_text,
                    'selector': error_selector,
                    'screenshot': 'error_banner.png'
                })
        
        # Check for specific error patterns
        page_text = page.content()
        for error_pattern in ErrorRegistry.DRAFTKINGS:
            if error_pattern.lower() in page_text.lower():
                errors.append({
                    'message': error_pattern,
                    'selector': 'page_text',
                    'screenshot': 'error_pattern.png'
                })
        
        # Count legs in betslip
        betslip_count = 0
        count_selector = SelectorRegistry.DRAFTKINGS['betslip_count']
        count_element = page.query_selector(count_selector)
        if count_element:
            count_text = count_element.text_content()
            try:
                betslip_count = int(count_text)
            except:
                pass
        
        status = "VALID" if not errors else "INVALID"
        
        return {
            'status': status,
            'legs_added': betslip_count,
            'legs_attempted': len(legs),
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"DraftKings validation error: {e}")
        return {
            'status': 'ERROR',
            'legs_added': 0,
            'legs_attempted': len(legs),
            'errors': [{'message': str(e), 'selector': 'exception', 'screenshot': 'error.png'}]
        }


def validate_betslip_bet365(page: Page, legs: List[Dict[str, Any]], args: argparse.Namespace) -> Dict[str, Any]:
    """Validate Bet365 betslip for errors."""
    try:
        logger.info("Validating Bet365 betslip...")
        
        # Similar logic but with Bet365 selectors
        errors = []
        error_selector = SelectorRegistry.BET365['error_banner']
        error_elements = page.query_selector_all(error_selector)
        
        for element in error_elements:
            error_text = element.text_content()
            if error_text:
                errors.append({
                    'message': error_text,
                    'selector': error_selector,
                    'screenshot': 'error_banner.png'
                })
        
        # Check for specific error patterns
        page_text = page.content()
        for error_pattern in ErrorRegistry.BET365:
            if error_pattern.lower() in page_text.lower():
                errors.append({
                    'message': error_pattern,
                    'selector': 'page_text',
                    'screenshot': 'error_pattern.png'
                })
        
        # Count legs in betslip
        betslip_count = 0
        count_selector = SelectorRegistry.BET365['betslip_count']
        count_element = page.query_selector(count_selector)
        if count_element:
            count_text = count_element.text_content()
            try:
                betslip_count = int(count_text)
            except:
                pass
        
        status = "VALID" if not errors else "INVALID"
        
        return {
            'status': status,
            'legs_added': betslip_count,
            'legs_attempted': len(legs),
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"Bet365 validation error: {e}")
        return {
            'status': 'ERROR',
            'legs_added': 0,
            'legs_attempted': len(legs),
            'errors': [{'message': str(e), 'selector': 'exception', 'screenshot': 'error.png'}]
        }


def run_for_book(book: str, legs: List[Dict[str, Any]], args: argparse.Namespace) -> Dict[str, Any]:
    """Run betslip simulation for a specific sportsbook."""
    start_time = time.time()
    
    try:
        logger.info(f"Starting simulation for {book}")
        
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(
                headless=not args.headed,
                slow_mo=args.slowmo_ms
            )
            
            # Create context with video recording if requested
            context_options = {
                'viewport': {'width': 1920, 'height': 1080},
                'locale': 'en-US',
                'timezone_id': 'America/New_York'
            }
            
            if args.video:
                context_options['record_video_dir'] = str(args.screenshot_dir / book)
            
            context = browser.new_context(**context_options)
            
            # Load state if available
            if not load_state(context, book):
                # Login
                page = context.new_page()
                
                if book == 'fanduel':
                    login_success = login_fanduel(page, args)
                elif book == 'draftkings':
                    login_success = login_draftkings(page, args)
                elif book == 'bet365':
                    login_success = login_bet365(page, args)
                else:
                    raise ValueError(f"Unknown book: {book}")
                
                if not login_success:
                    return {
                        'book': book,
                        'status': 'ERROR',
                        'legs_added': 0,
                        'legs_attempted': len(legs),
                        'errors': [{'message': 'Login failed', 'selector': 'login', 'screenshot': 'login_failed.png'}],
                        'duration': time.time() - start_time
                    }
                
                # Save state after successful login
                save_state(context, book)
            
            # Navigate to game
            page = context.new_page()
            
            if book == 'fanduel':
                nav_success = navigate_to_game_fanduel(page, args)
            elif book == 'draftkings':
                nav_success = navigate_to_game_draftkings(page, args)
            elif book == 'bet365':
                nav_success = navigate_to_game_bet365(page, args)
            else:
                raise ValueError(f"Unknown book: {book}")
            
            if not nav_success:
                return {
                    'book': book,
                    'status': 'ERROR',
                    'legs_added': 0,
                    'legs_attempted': len(legs),
                    'errors': [{'message': 'Navigation failed', 'selector': 'navigation', 'screenshot': 'nav_failed.png'}],
                    'duration': time.time() - start_time
                }
            
            # Add legs to betslip
            legs_added = 0
            for i, leg in enumerate(legs):
                try:
                    if book == 'fanduel':
                        success = add_leg_fanduel(page, leg, args)
                    elif book == 'draftkings':
                        success = add_leg_draftkings(page, leg, args)
                    elif book == 'bet365':
                        success = add_leg_bet365(page, leg, args)
                    else:
                        raise ValueError(f"Unknown book: {book}")
                    
                    if success:
                        legs_added += 1
                        screenshot(page, args.screenshot_dir / book, f"02_leg_{i}_added")
                    
                except NotImplementedError as e:
                    logger.warning(f"Market not implemented: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error adding leg {i}: {e}")
                    continue
            
            # Validate betslip
            if book == 'fanduel':
                result = validate_betslip_fanduel(page, legs, args)
            elif book == 'draftkings':
                result = validate_betslip_draftkings(page, legs, args)
            elif book == 'bet365':
                result = validate_betslip_bet365(page, legs, args)
            else:
                raise ValueError(f"Unknown book: {book}")
            
            # Cleanup if not dry run
            if not args.dry_run:
                # Clear betslip
                clear_selector = SelectorRegistry.FANDUEL['clear_betslip'] if book == 'fanduel' else \
                               SelectorRegistry.DRAFTKINGS['clear_betslip'] if book == 'draftkings' else \
                               SelectorRegistry.BET365['clear_betslip']
                
                clear_button = page.query_selector(clear_selector)
                if clear_button:
                    clear_button.click()
                    page.wait_for_timeout(1000)
            
            # Final screenshot
            screenshot(page, args.screenshot_dir / book, "03_final_state")
            
            browser.close()
            
            result['book'] = book
            result['duration'] = time.time() - start_time
            return result
            
    except Exception as e:
        logger.error(f"Error running simulation for {book}: {e}")
        return {
            'book': book,
            'status': 'ERROR',
            'legs_added': 0,
            'legs_attempted': len(legs),
            'errors': [{'message': str(e), 'selector': 'exception', 'screenshot': 'error.png'}],
            'duration': time.time() - start_time
        }


def summarize(results: List[Dict[str, Any]]) -> None:
    """Print summary table of results."""
    print("\n" + "="*80)
    print("BETSLIP SIMULATION RESULTS")
    print("="*80)
    print(f"{'BOOK':<12} {'STATUS':<8} {'LEGS_OK/LEGS_TOTAL':<18} {'ERRORS':<8} {'NOTES'}")
    print("-"*80)
    
    for result in results:
        book = result['book']
        status = result['status']
        legs_ok = result['legs_added']
        legs_total = result['legs_attempted']
        errors = len(result['errors'])
        
        notes = ""
        if status == 'ERROR':
            notes = "Login/navigation failed"
        elif status == 'INVALID':
            notes = f"Betslip errors: {', '.join([e['message'][:30] for e in result['errors'][:2]])}"
        elif status == 'VALID':
            notes = "All legs valid"
        
        print(f"{book:<12} {status:<8} {legs_ok}/{legs_total:<12} {errors:<8} {notes}")
    
    print("="*80)


def main():
    """Main entry point."""
    args = parse_args()
    
    # Handle logout flag
    if args.logout:
        for book in args.books:
            clear_state(book)
        print("Storage states cleared")
        return
    
    # Validate credentials
    credentials_status = validate_credentials(args.books)
    missing_credentials = [book for book, has_creds in credentials_status.items() if not has_creds]
    
    if missing_credentials and not args.manual_login:
        print("❌ Missing credentials for the following books:")
        for book in missing_credentials:
            if book == 'fanduel':
                print(f"   {book}: FANDUEL_EMAIL, FANDUEL_PASSWORD")
            elif book == 'draftkings':
                print(f"   {book}: DRAFTKINGS_EMAIL, DRAFTKINGS_PASSWORD")
            elif book == 'bet365':
                print(f"   {book}: BET365_USERNAME, BET365_PASSWORD")
        
        print("\n💡 Solutions:")
        print("   1. Copy .env.example to .env and fill in your credentials")
        print("   2. Set environment variables directly")
        print("   3. Use --manual-login flag to handle login manually")
        print("\n📝 Example .env file:")
        print("   FANDUEL_EMAIL=your_email@example.com")
        print("   FANDUEL_PASSWORD=your_password")
        print("   DRAFTKINGS_EMAIL=your_email@example.com")
        print("   DRAFTKINGS_PASSWORD=your_password")
        print("   BET365_USERNAME=your_username")
        print("   BET365_PASSWORD=your_password")
        sys.exit(2)
    
    # Handle MFA prompt if requested
    if args.mfa_prompt and not args.mfa_code:
        print("\n🔐 MFA Setup")
        print("You can provide MFA codes in several ways:")
        print("   1. Use --mfa-code flag with the code")
        print("   2. Use --mfa-prompt for interactive prompts")
        print("   3. Use --manual-login to handle everything manually")
        print("   4. Set MFA codes in environment variables (see .env.example)")
        print()
        
        # Prompt for each book
        for book in args.books:
            if credentials_status.get(book, False):
                mfa_code = prompt_for_mfa_code(book)
                # Store in args for use during login
                setattr(args, f'{book}_mfa_code', mfa_code)
    
    # Create screenshot directory
    ensure_dir(args.screenshot_dir)
    
    # Load legs
    legs = load_legs(args.legs_json)
    
    # Print summary
    print(f"Betslip Simulator")
    print(f"Books: {', '.join(args.books)}")
    print(f"Sport: {args.sport_key}")
    print(f"Game ID: {args.game_id}")
    print(f"Legs: {len(legs)}")
    print(f"Screenshot dir: {args.screenshot_dir}")
    print(f"Dry run: {args.dry_run}")
    print()
    
    # Run simulation for each book
    results = []
    for book in args.books:
        result = run_for_book(book, legs, args)
        results.append(result)
    
    # Print summary
    summarize(results)
    
    # Save results to JSON
    summary_path = args.screenshot_dir / "summary.json"
    with open(summary_path, 'w') as f:
        # Convert PosixPath objects to strings for JSON serialization
        args_dict = vars(args)
        args_dict['legs_json'] = str(args_dict['legs_json'])
        if args_dict.get('screenshot_dir'):
            args_dict['screenshot_dir'] = str(args_dict['screenshot_dir'])
        
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'args': args_dict,
            'results': results
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: {summary_path}")
    
    # Determine exit code
    all_valid = all(r['status'] == 'VALID' for r in results)
    any_error = any(r['status'] == 'ERROR' for r in results)
    
    if any_error:
        sys.exit(2)  # Fatal error
    elif not all_valid:
        sys.exit(1)  # Invalid combinations
    else:
        sys.exit(0)  # All valid


if __name__ == "__main__":
    main()
