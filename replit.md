# Bot du Millionnaire - Solana Copy Trading

## Overview

Bot du Millionnaire is an automated Solana copy trading application that monitors and replicates trades from selected Solana traders. The bot provides real-time portfolio tracking, performance analytics, and configurable trading parameters through a modern web interface. It supports both TEST mode (simulation with virtual capital) and REAL mode (actual blockchain transactions).

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Updates (Phase 9 - Helius API Integration Complete)

### 🚀 Phase 9: Full Helius API Integration (November 25, 2025)

**Helius API Successfully Integrated! 🎉**

**What was fixed:**
1. ✅ **API Response Format**: Adapted code to handle Helius returning direct transaction list (not wrapped in dict)
2. ✅ **Transaction Parsing**: Fixed parsing to accept pre-parsed transaction objects from Helius
3. ✅ **`.env` Configuration**: Bot now loads Helius API keys from `.env` file automatically
4. ✅ **Diagnostic Tool**: Created `test_helius_api.py` script to verify API connectivity and detect SWAPs
5. ✅ **Status Verification**: Bot shows "✅ Helius API Key: Configurée" at startup

**Test Results:**
- ✅ **Euris**: 98 transactions found
- ✅ **Starter**: 96 transactions found, **1 SWAP DETECTED** 
- ✅ **Italie**: 100 transactions found

**Files Created/Modified:**
- `copy_trading_simulator.py`: Updated `get_trader_recent_trades()` to parse Helius list format
- `test_helius_api.py`: Diagnostic script for testing API and SWAP detection
- `.env`: Helius API key configuration file
- `SETUP_LOCAL.md`: Documentation for local setup

**How It Works Now:**
1. Bot starts → loads `.env` with `HELIUS_API_KEY`
2. For each active trader → fetches transactions from Helius
3. Identifies SWAP transactions automatically
4. Simulates trades with virtual capital in TEST mode
5. Displays PnL in dashboard

## Recent Updates (Phase 8 - Local Setup + Trade Detection Fix)

### 🔧 Phase 8: Trade Detection Infrastructure (November 24, 2025)

**Issue Resolved**: Bot n'affichait AUCUN trade copié en mode TEST
- **Root cause**: `HELIUS_API_KEY` n'était pas définie
- **Solution**: Vérification + logging amélioré au démarrage

**Improvements Made**:
1. ✅ **Cycle de détection accéléré**: 120s → 5s (ultra-rapide pour meme coins)
2. ✅ **Logging détaillé**: Affiche status API key + traders actifs + bot state au démarrage
3. ✅ **Support fichier `.env`**: Charge variables d'environnement depuis `.env` en local
4. ✅ **Documentation locale**: Ajout de `SETUP_LOCAL.md` pour configuration ordinateur
5. ✅ **Template `.env.example`**: Guide pour l'utilisateur

**Configuration Status (au démarrage)**:
```
============================================================
✅ BOT PRÊT À DÉMARRER
Mode: TEST
Helius API Key: ✅ Configurée
Traders actifs: 3
Bot activé: ❌ NON (L'utilisateur doit cliquer pour activer)
============================================================
```

**Capital assigné aux traders**:
- Japon: 100 USD (corrigé de 0)
- Colombie: 100 USD
- Scalper: 100 USD

**Prochaines étapes pour l'utilisateur**:
1. Activer le bot via le dashboard ("Activer/Désactiver Bot")
2. Attendre 5-10 secondes que les trades se copient
3. Vérifier les logs pour voir: "✅ N trades détectés"

### ✅ Phase 6 Complete - Auto Sell + Backtesting + Benchmark
- **Auto Sell Manager**: Automatic position management (TP/SL or mirror exact trader sales)
- **Backtesting Engine**: Test 30+ TP/SL combinations to identify best parameters
- **Benchmark System**: Compare bot performance vs selected traders with ranking

### 🚀 Phase 7 - LIVE Dashboard avec Tokens en Temps Réel (November 24, 2025)
**Nouveau onglet "⚡ LIVE TRADING"** pour monitoring temps réel :
- **Affichage tokens**: Vois quels tokens sont en trading par chaque trader
- **Mises à jour 1s**: Données actualisées en continu (ultra-rapide)
- **Indicateurs visuels**: 🟢 Rentable vs 🔴 En perte
- **Actions directes**: 
  - 💰 Sortir Tout = Close toutes positions du trader
  - ❌ Désactiver = Arrête ce trader
- **Stats en direct**: PnL 24h, Win Rate, Positions ouvertes

## System Architecture

### Frontend Architecture

**Technology Stack:**
- Pure HTML/CSS/JavaScript embedded in Flask template
- Single-page application with tab-based navigation
- Real-time updates via periodic AJAX polling (every 2 seconds)

**Design Decisions:**
- **No external frameworks**: Uses vanilla JavaScript to minimize dependencies and deployment complexity
- **Inline styling**: All CSS embedded in HTML template for portability
- **Tab-based UI**: Four main sections (Dashboard, Traders, Settings, History) for organized user experience
- **Visual feedback**: Color-coded status indicators, emoji icons, and real-time PnL displays

### Backend Architecture

**Core Framework:**
- Flask web server (single-threaded with background workers)
- Python 3.9+ required for compatibility with Solana libraries

**Key Components:**

1. **BotBackend (bot_logic.py)**: Central configuration manager
   - Loads/saves configuration from `config.json`
   - Manages trader selection (max 3 active traders)
   - Handles virtual balance in TEST mode
   - Validates configuration integrity on startup

2. **Portfolio Tracker (portfolio_tracker.py)**: Real-time wallet monitoring
   - Tracks Solana wallet values via RPC calls
   - Calculates PnL (Profit & Loss) for each trader
   - Maintains historical data with automatic cleanup (8-day retention)
   - Implements caching (2-minute TTL) to avoid RPC rate limiting
   - Background thread updates every 2 minutes

3. **Copy Trading Simulator (copy_trading_simulator.py)**: TEST mode transaction simulation
   - Retrieves actual transactions from Helius API
   - Simulates trades with virtual capital allocation
   - Calculates realistic PnL based on simulated trades
   - Persists simulated trades to JSON and SQLite

4. **Trade Management System**:
   - **Trade Validator (trade_validator.py)**: Pre-execution safety checks with configurable validation levels (STRICT/NORMAL/RELAXED)
   - **Trade Safety (trade_safety.py)**: Take Profit (TP) and Stop Loss (SL) management with three configurable TP levels
   - **DEX Handler (dex_handler.py)**: Multi-DEX support (Raydium, Orca, Jupiter, Magic Eden)

5. **Monitoring & Logging**:
   - **Audit Logger (audit_logger.py)**: Security-focused logging with multiple log levels (DEBUG through SECURITY)
   - **Performance Monitor (monitoring.py)**: Real-time metrics collection, alerting system
   - **Metrics Collector**: Tracks hourly/daily statistics

6. **Blockchain Integration**:
   - **Solana Integration (solana_integration.py)**: RPC connection wrapper and address validation
   - **Helius Integration (helius_integration.py)**: Enhanced transaction parsing for swap detection
   - **Solana Executor (solana_executor.py)**: Transaction signing and submission for REAL mode

**Architecture Patterns:**

- **Configuration as Code**: All settings persisted in `config.json` with runtime validation
- **Dual Storage Strategy**: 
  - JSON files for immediate access and human readability
  - SQLite database for long-term persistence and complex queries
- **Background Processing**: Separate daemon thread for portfolio tracking to avoid blocking web requests
- **Rate Limiting Protection**: Built-in caching and delays between RPC calls
- **Security-First Design**: Private keys stored only in memory, never persisted to disk

**Trade Execution Flow (REAL mode):**
1. Detect trader transaction via Helius API
2. Validate trade parameters through TradeValidator
3. Calculate position size based on trader capital allocation
4. Apply slippage tolerance and TP/SL levels
5. Execute swap via DEX Handler
6. Monitor trade status through Portfolio Tracker
7. Log execution to Audit Logger

**Trade Simulation Flow (TEST mode):**
1. Retrieve recent trades from trader wallets
2. Simulate execution with virtual capital
3. Calculate theoretical PnL based on market prices
4. Update portfolio tracker with simulated results

### Data Storage Solutions

**Primary Storage:**
- **config.json**: User configuration, trader settings, TP/SL parameters
- **portfolio_tracker.json**: Current portfolio state, historical values, PnL calculations
- **simulated_trades.json**: TEST mode trade history
- **config_tracker.json**: Portfolio tracking configuration

**Database (SQLite - bot_data.db):**
- **wallet_history**: Time-series wallet balance data
- **trader_portfolio**: Aggregated trader performance metrics
- **portfolio_history**: Historical portfolio snapshots
- **simulated_trades**: Long-term trade simulation records
- **benchmark_data**: Performance comparison data
- **audit_logs**: Security and operational logs

**Rationale:**
- JSON for hot data and user-facing configuration (fast reads, easy debugging)
- SQLite for historical data and analytics (efficient queries, data integrity)
- No external database server required (simplified deployment)

### Authentication and Authorization

**Current Implementation:**
- Session-based private key storage (in-memory only)
- Private key entered via web UI for REAL mode
- Automatic key clearing on disconnect/logout

**Security Measures:**
- Private keys never written to config.json
- No logging of sensitive key material
- Audit trail excludes cryptographic secrets
- Environment variable support for API keys (HELIUS_API_KEY, RPC_URL)

**Design Decision:**
The application prioritizes simplicity over multi-user authentication. It's designed for single-user operation with session-based security rather than complex user management systems.

### External Dependencies

**Blockchain Services:**

1. **Solana RPC Endpoints**:
   - Default: `https://api.mainnet-beta.solana.com` (public mainnet)
   - Purpose: Wallet balance queries, transaction retrieval
   - Configurable via `RPC_URL` environment variable

2. **Helius API** (Optional but Recommended):
   - Purpose: Enhanced transaction parsing, swap detection
   - Rate limits: Free tier suitable for moderate use
   - API key via `HELIUS_API_KEY` environment variable
   - Fallback: Standard RPC if unavailable

**Python Libraries:**

Required (requirements.txt):
- `flask==3.0.0`: Web framework
- `requests==2.31.0`: HTTP client for RPC/API calls

Optional (graceful degradation if missing):
- `solders`: Solana key management (keypair operations)
- `solana`: Official Solana Python SDK
- `base58`: Address validation

**External Price Feeds:**
- CoinGecko API (implicit, through RPC metadata)
- Used for SOL/USD conversion in portfolio valuation

**DEX Integrations:**
- Jupiter Aggregator (planned for swap routing)
- Raydium, Orca (protocol-level integration)
- Magic Eden (NFT/token swaps)

**Design Decisions:**

- **Minimal Dependencies**: Only Flask and requests are required; Solana libraries optional for TEST mode
- **Graceful Fallbacks**: Application works in simulation mode without blockchain connectivity
- **No Database Server**: SQLite eliminates external database dependency
- **API Key Management**: Environment variables for secrets, never hardcoded
- **Rate Limit Awareness**: Built-in delays and caching to respect public RPC limits

**Deployment Considerations:**
- Works on Replit with minimal configuration
- macOS compatible (conditional imports handle platform differences)
- Port 5000 default (configurable)
- No compilation or build step required