# Forecasting & Prediction Handbook

A practical handbook distilled from nine lecture decks (MS_slides01–09, *Forecasting and Time Series Analysis*, William Yu, UCLA Anderson Forecast). It is organised as a workflow you can follow on any forecasting or prediction project, with the deck each idea comes from noted as `[S#]`.

**Contents**

1. [Mindset: signal, noise, and what "forecastable" means](#1-mindset)
2. [Project workflow checklist](#2-project-workflow-checklist)
3. [Know your data: cross-section, time series, panel](#3-know-your-data)
4. [Explore first: always plot](#4-explore-first)
5. [Correlation, causation, and the traps](#5-correlation-causation-and-the-traps)
6. [Regression essentials and interpretation](#6-regression-essentials)
7. [Transformations: logs and growth rates](#7-transformations)
8. [Decomposing a series: trend, seasonality, cycle](#8-decomposing-a-series)
9. [Stationarity and autocorrelation](#9-stationarity-and-autocorrelation)
10. [Model families and when to use each](#10-model-families)
11. [Many predictors: dimension reduction](#11-many-predictors)
12. [Structural change and time-varying parameters](#12-structural-change)
13. [Validation and evaluation](#13-validation-and-evaluation)
14. [Neural nets, LSTM, LLMs: where they fit](#14-neural-nets-lstm-llms)
15. [Common pitfalls](#15-common-pitfalls)
16. [Model-choice cheat sheet](#16-model-choice-cheat-sheet)
17. [Further reading](#17-further-reading)

---

## 1. Mindset

**Data = signal + noise.** [S1]
- *Signal* (pattern, order, information) repeats, so it is what makes forecasting possible.
- *Noise* (shocks, idiosyncrasy, chaos) does not repeat.
- Signal-to-noise ratio decides difficulty: high is easy to predict, low is hard.

**Four kinds of analytics** [S1]

| Type | Question | Typical tool |
|---|---|---|
| Descriptive | What happened? | plots, dashboards, EDA, mean/SD, growth rates |
| Diagnostic | Why did it happen? | `Y = α + βX` |
| Predictive | What will happen? | `Y(t+1) = α + βX(t)` or `Y(t+1) = α + βY(t)` |
| Prescriptive | What should we do? | decision/strategy, value creation |

**Time-series forecasting is harder than cross-section prediction** [S1]. Cross-sectional data share one period and one signal. In a time series the signal itself can change at T+1, T+2 (new "state", new pattern). Time dependence is a double-edged sword: a single series is easy to extrapolate, but it is a biased sample of the whole population (e.g. 10 people polled weekly for 100 weeks ≠ 1,000 people polled now; one reviewer's many reviews ≠ objective review).

**Some series are simply not forecastable** [S3]: white noise and stock-price *returns* have no autocorrelation; stock *prices* are non-stationary random walks; housing returns are predictable "to some degree".

**Match the model's horizon to the question** [S4]:
- Long-term: focus on trend (supply side: capital, labour, human capital, technology).
- Medium-term: focus on the cycle (demand side, output gap, rates).
- Short-term / high-frequency: focus on noise.

**Use AI assistants freely, but verify.** Test generated code in a safe environment, understand it before using it, and ask for clarification when unsure. [S1]

---

## 2. Project workflow checklist

1. **Define the question and the horizon.** Descriptive, diagnostic, predictive or prescriptive? One-step or *h*-step ahead? Real-time or retrospective?
2. **Get and inspect the data.** Frequency, units, seasonally adjusted (SA) or not (NSA, raw data usually NSA), missing values, ID columns to drop. [S2, S3]
3. **Plot everything** (time plot, seasonal plot, scatter, map, correlation matrix, ACF/PACF). [S1, S3, S4]
4. **Decide the target form**: level, log, growth rate, or difference. [S2, S4]
5. **Identify components**: trend, seasonality, cycle, breaks, outliers. [S3, S8]
6. **Test stationarity** (plot, ACF, unit-root test) and transform if needed. [S3, S4]
7. **Build a simple baseline first** (naive / trend / seasonal / AR). Add complexity only when it earns out-of-sample gains (KISS). [S1]
8. **Candidate models**: structural/regression, reduced-form (ARIMA), mixed (ARDL/ARIMAX), VAR, factor, state-space, ML/DL. [S1, S4–S9]
9. **Validate out-of-sample** with time-ordered splits and rolling windows, never random shuffles. [S4, S8]
10. **Diagnose residuals** (white noise? autocorrelation? heteroskedasticity?). [S2, S5]
11. **Compare with loss functions** (RMSE, MAE, MSLE) and information criteria (AIC/BIC). [S2]
12. **Re-estimate and monitor** for structural change; consider combining models. [S8]

---

## 3. Know your data

| Structure | Rows are | Key tool |
|---|---|---|
| Cross-sectional | entities at one time (firms, counties) | correlation / OLS |
| Time series | one entity over time (t1…T) | **autocorrelation** / ACF |
| Panel | entity × time | fixed / random effects |

Terminology [S1]: `y` = dependent / response / label; `x` = independent / explanatory / features / predictors / covariates. **Long data** (large n) is better than **fat data** (large p). Degrees of freedom = n − (p+1); larger is better. A cross-section ID column is just an identifier and should not be used as a feature. [S2]

Train/test: in cross-section the test rows are a random subset; in time series the test rows are the **future** (t9…T), so order matters. [S1]

### Panel data models [S2]

| Model | Equation | Idea |
|---|---|---|
| Pooling OLS | `Y_it = α + βX_it + e_it` | needs strict exogeneity; ignores entity differences |
| Entity fixed effect | `Y_it = βX_it + C_i + e_it` | `C_i` constant per entity, may correlate with X; uses variation **within** entities |
| Random effect | `Y_it = α + βX_it + C_i + e_it` | `C_i` random and uncorrelated with X |
| Time fixed effect | `Y_it = βX_it + C_t + e_it` | common shocks per period |

- OLS can show the wrong sign when entities differ (medical expense vs life expectancy: OLS says no relation, FE says positive). In the election example the OLS beta was 0.23 versus FE 0.53.
- Panel data raises the chance of identifying causality rather than mere correlation.
- Time fixed effects are not available for a real-time forecast (future period dummies are unknown), whereas regional fixed effects are.
- Add lags (`Y_{t-1}`, `Y_{t-2}`) within each entity to make a dynamic panel.
- Residual problems: heterogeneity across firms/years and autocorrelation within entity.

---

## 4. Explore first

**Always plot your data** [S1]:
- Geographic pattern (maps), time-series pattern (many series on one chart), two-variable correlation (scatter with fitted line).
- Look for level shifts, trend, seasonal bumps, outliers, regime changes, and divergence between groups.

Useful plots: time plot, seasonal plot by month/year, sub-series plot, scatter and correlation matrix, ACF/PACF, histogram before and after log. [S2, S3, S4]

---

## 5. Correlation, causation, and the traps

- Correlation has **no direction**; regression *implies* X → Y. [S1]
- **Spurious correlation**: unrelated series that trend together (Fed chair height vs interest rates; two trending series). Spurious fits give wrong predictions and decisions. [S1]
- **Confounders**: ice-cream and sunburn are both driven by hot sun. Unobserved confounders cause *omitted-variable bias*. [S1]
- **Reverse causality / simultaneity**: happiness ↔ marriage. X should be as exogenous as possible. [S1]
- **Ladder of causation** [S1]:
  1. Seeing: P(Y | observe X), from passive data.
  2. Doing: P(Y | do X), from experiments (RCT).
  3. Imagining: counterfactuals, "what if X had not occurred?"

  (A rooster crowing predicts dawn but does not cause it.)
- **RCT**: treatment dummy (1 treated, 0 control); a significant β means the treatment matters. Multivariate regression controls for confounders. [S1]
- **Difference-in-Differences (DID)** [S2]: `Y = β0 + β1·Time + β2·Intervention + β3·(Time×Intervention) + β4·Covariates + ε`
  - β1: time trend in control. β2: pre-intervention gap. **β3: the treatment effect** (difference in changes).
  - Needs the **parallel-trends assumption**; treatment assignment is not random.
  - A/B test = randomised, snapshot; DID = quasi-experimental, before/after, for policy and economic impacts.
- **Granger causality** [S6]: asks whether the history of y2 helps predict y1 beyond y1's own history (φ12 ≠ 0). It is *predictive* usefulness, **not true causality**.
- **Lead–lag check** [S5]: levels of two trending series may fail a lead test while their **changes** pass (ΔY_t = α + βΔX_{t-1}); test in differences.

**Regression-to-the-mean** [S3]: with an AR coefficient below 1 (e.g. child height ≈ 42 + 0.7·parent), extremes drift back toward the mean. A coefficient ≥ 1 gives a non-stationary process.

---

## 6. Regression essentials

`Y = α + βX + e` fitted by OLS minimising Σe² = Σ(Y − Ŷ)². [S1]

- The error `e` should behave like noise. If X and e are correlated you get omitted-variable bias or simultaneity bias. [S2]
- Remedies for correlated errors / bias [S2]: add lags, instrumental variables, DID, **HAC (robust) standard errors**, **clustered standard errors**.
- OLS assumes iid, homoskedastic errors; panel and time-series residuals often violate that.
- Dummy variables: use k−1 dummies for k categories to avoid the dummy trap (multicollinearity with the intercept). [S3]
- Linear = incremental relationship; non-linear = turning-point relationship (all tree models, random forest, XGBoost, neural nets are non-linear). [S2]

### Coefficient interpretation [S2]

| Model | Meaning of β |
|---|---|
| `y = α + βX` | 1 unit ↑ X → β units change in y |
| `y = α + β ln X` (linear-log) | 1 % ↑ X → 0.01β units change in y |
| `ln y = α + βX` (log-linear) | 1 unit ↑ X → 100β % change in y |
| `ln y = α + β ln X` (log-log) | 1 % ↑ X → β % change in y (elasticity) |

---

## 7. Transformations

Why use logs [S2]:
1. Turn a non-linear (exponential) form into a linear one.
2. A straight line in log scale means a **constant growth rate** (in original scale, constant change).
3. Pull skewed data toward a more normal shape (e.g. GDP across countries).

Growth rates [S2]:
- Simple: `Y_t / Y_{t-1} − 1`
- Continuously compounded: `ln Y_t − ln Y_{t-1}` (0.06 ≈ 6 %)
- CAGR: `(End / Begin)^(1/years) − 1`

Other transformations for stationarity [S4]: Box-Cox, detrend (deterministic trend), first difference (stochastic trend), growth rate. Convert a multiplicative model to additive with logs. [S3]

---

## 8. Decomposing a series

**Time series = trend + cycle + seasonal + noise.** [S3]

### Trend models (long-run) [S3]
| # | Model | Note |
|---|---|---|
| 1 | Linear `Y = β0 + β1·t` | simplest |
| 2 | Quadratic / polynomial | curvature |
| 3 | Log-linear `ln Y = β0 + β1·t` | constant growth rate |
| 4 | Simple moving average MA(k) | forecast = mean of last k |
| 5 | Exponential smoothing | `Ŷ_{t+1} = αY_t + (1−α)Ŷ_t`; larger α puts more weight on new data |
| 6 | Holt's method | level + trend slope equations, optional damping φ in (0,1) |
| 7 | Logistic (S-curve) | `K / (1 + e^{-r(t−t0)})`; carrying capacity K, growth rate r, inflection t0; for adoption, epidemics, product life cycles |

Trend is easiest to see at low frequency and matters most for long-term forecasts. Deterministic trends fit; stochastic trends need differencing (see §9).

### Seasonality [S3, S4]
- Know whether data are SA or NSA; raw data are usually NSA.
- **Method 1: seasonal dummies** `y = α + β·Trend + Σγ·Month_i` (use m−1 dummies).
- **Method 2: seasonal plots** and seasonal sub-series to inspect patterns.
- **Additive** `Y = T + S + e` when seasonal swings are constant; **multiplicative** `Y = T × S × e` when swings scale with the level (log it to make it additive).
- **SARIMA** handles it through seasonal terms (§10); frequency m: annual 1, quarterly 4, monthly 12, weekly 52, daily 7 or 365.

### Cycle [S3, S4]
Anything dynamic not captured by trend and seasonality; modelled with stationary ARMA-type dynamics after trend and seasonality are handled. Real housing prices, for example, show repeated boom–bust cycles.

**Caution:** popular automated libraries (e.g. Prophet) can produce questionable trend extrapolations; inspect trend, weekly, and yearly components yourself. [S3]

---

## 9. Stationarity and autocorrelation

**Stationary** (necessary for forecasting cycles) [S3]: stable mean, stable variance and covariance over time. Check by: view the graph, check the ACF, run a unit-root test.

**ACF** `ρ_τ = cov(Y_t, Y_{t−τ}) / var(Y)`: the correlation of a series with its own lags. [S3]
- Stationary → ACF decays quickly (geometrically).
- Non-stationary / trending → ACF stays near 1 and decays very slowly. (That does *not* mean high true predictability.)
- White noise → no significant spikes (dashed lines are the critical bounds, like a Ljung-Box test).
- More persistent series can be forecast further ahead.

**Deterministic vs stochastic trend** [S4]

| | Stationary / deterministic trend | Stochastic trend (random walk) |
|---|---|---|
| Shocks | temporary | permanent |
| Behaviour | mean-reverting | no return to trend |
| ACF | dies out exponentially | hardly dies |
| Process | I(0); AR(1) with β < 1 | I(1); AR(1) with **β = 1** (unit root) |

Fix non-stationarity by transforming: logs, detrend, or difference (levels of GDP and payrolls are non-stationary; their growth rates/changes are stationary). [S4]

---

## 10. Model families

### 10.1 Three predictive architectures [S1]

| Type | Form | Use |
|---|---|---|
| **Structural / static** | `y_t = α + βx_t + ε` | explains y from drivers; needs future X → scenario analysis, or use lagged X |
| **Reduced form / autoregressive** | `y_t = f(y_{t-1}, y_{t-2}, …)` | forecast recursively (chain rule): predict t+1, then t+2 … |
| **Mixed / dynamic regression (ADL)** | `y_t = f(y_{t-1}, x_t, …)` | both inertia and drivers |

Structural example: California's VMT regressed on population, housing starts, gas price, income for 5-year projections.

### 10.2 Box–Jenkins family [S4]
- **AR(p)**: regress on own p lags. **MA(q)**: on past forecast errors. **ARMA(p,q)** combines them.
- Pick orders: AR → look at **PACF** cut-off; MA → look at **ACF** cut-off. PACF is the correlation at lag k after removing shorter lags.
- **ARIMA(p,d,q)**: difference d times for stationarity, then ARMA. ARIMA(0,0,0) white noise; (p,0,0) AR; (0,0,q) MA; (0,1,0) pure random walk (unpredictable); (p,1,q) random walk with dynamics; (0,1,0)+drift.
- **SARIMA(p,d,q)(P,D,Q)_m** adds seasonal AR, differencing, and MA at multiples of m (e.g. m = 12: y_{t−12}, y_{t−24}; seasonal difference y_t − y_{t−12}).
- **Wold decomposition** [S6]: any stationary process is an infinite MA of white noise; ARMA/ARIMA are finite approximations.

### 10.3 Dynamic regression (drivers + dynamics) [S5]

| Model | Form | Key point |
|---|---|---|
| Distributed lag (DL) | `y_t = α + β1·x_{t-1} + β2·x_{t-2} + …` | delayed effect of X; total effect = Σβ |
| **ARDL** | lags of y **and** x | inertia plus gradual response; long-run multiplier = `Σβ_x / (1 − Σφ_y)`; if truth is ARDL but you fit DL you get bias; the reverse is less harmful |
| Regression with ARIMA errors | `y = α + βx + η`, η ~ ARIMA | explain y by x while fixing autocorrelated residuals |
| **ARIMAX / SARIMAX** | ARIMA on y plus exogenous regressors (`auto.arima(y, xreg = X)`) | forecast a series driven by external inputs |

ARDL intuition: the lagged-Y term (β1) predicts inertia; the X term (β2) helps predict **turning points and structural change**; unobserved drivers fall into the error. Example: `PropertyTax_t = α + β1·PropertyTax_{t−1} + β2·Jobs_{t−1} + β3·HousingValue_{t−1} + e`. All of these assume X is exogenous.

### 10.4 VAR [S6]
- When X and Y influence each other, model **all variables jointly**: each variable regressed on p lags of itself and of every other variable (e.g. GDP growth, unemployment, inflation, fed funds rate).
- **Granger causality** tests whether one variable's lags matter for another (not true causality).
- **Impulse response functions**: how variable i responds over time to a one-time shock to variable j (a shock is an event outside the VAR's prediction, e.g. COVID for GDP, a war for prices).

### 10.5 Dynamic factor model (PCA + VAR) [S7]
`x_t = ΛF_t + e_t`, `F_t = φF_{t−1} + e_t`: compress many series into a few factors, then forecast the factors with AR/VAR.

### 10.6 State-space and Kalman filter [S8]
- **Measurement**: `y_t = β_t x_t + e_t` (noise R). **Transition**: `β_t = u + Fβ_{t−1} + v_t` (noise Q). Parameters may vary over time.
- **Kalman filter** is a recursive predict → update procedure: *best estimate = old prediction + gain × prediction error*; the gain K_t shifts weight to new data when measurement noise R is small.
- **Structural time series** (local level, local linear trend, BSM with seasonal; Bayesian BSTS) and the R package KFAS support trend, seasonality, cycle, regressors, missing data, and non-Gaussian cases.

### 10.7 Panel / quasi-experimental models
See §3 (fixed/random effects) and §5 (DID).

---

## 11. Many predictors

"Tall" data (many rows) helps; "fat" data (many columns) can hurt. With p candidate variables there are 2^p models (2^40 ≈ 1 trillion). [S7]

Ways to cut down [S7]:
- Remove highly correlated variables (|ρ| > 0.95).
- Variance Inflation Factor (VIF).
- Stepwise / model-selection methods.
- Shrinkage: **Lasso, Ridge**.
- **PCA**: build uncorrelated components (loading vectors φ) that capture most variance; choose components using the variance-explained (scree) plot. Eigenvectors are the loadings; **SVD** `X = UΣVᵀ` gives the same components, with squared singular values equal to eigenvalues.
- **Dynamic factor model** to forecast the extracted factors.

---

## 12. Structural change

- Standard models assume constant α, β; in practice they may be **time-varying**. Note: stationarity concerns the *series*; structural change concerns the *parameters*. [S8]
- Tests: **Chow** (known break date), **Andrews / sup-F** (unknown break date), multiple-break methods (Bai–Perron style). If every period is a break the trend behaves like a random walk. [S8]
- Responses: model the breaks (dummies, split samples), rolling-window re-estimation, or time-varying-parameter / state-space models.

---

## 13. Validation and evaluation

### 13.1 In-sample vs out-of-sample [S1, S2]
- Split history into **train (in-sample)** and **test (out-of-sample)** sets; the future is the forecast period.
- A flexible non-linear fit can match history perfectly yet **overfit** and forecast badly; a simple linear model (KISS) often forecasts fine.

### 13.2 Selection criteria [S2]
- **In-sample**: residuals look like white noise; higher adjusted R²; higher likelihood; lower **AIC** or **BIC/SIC** (BIC penalises larger models more); Box-Pierce / **Ljung-Box** tests on residual autocorrelation.
- **Out-of-sample** forecast error `e_t = Ŷ_t − Y_t` with loss functions:

| Loss | Property |
|---|---|
| MSE | penalises large errors |
| RMSE | same units as the target |
| MAE | robust to outliers |
| MSLE | relative scale; compares across variables with different levels |

### 13.3 Time-series cross-validation [S4, S8]
Never shuffle. Use expanding or rolling origins (one-step-ahead, four-step-ahead, … *h*-step-ahead).

| Method | Setup | When / caveat |
|---|---|---|
| **I** | Fit on train, predict test **using actual future X** | most accurate but **look-ahead bias / data leakage** in real time; OK only when you control or know future X (scenarios) |
| **II** | Fit once, forecast the whole test window (X also forecast; reduced-form, trend, seasonal models) | least accurate (long out-of-sample horizon) |
| **III** | Rolling window, **fixed β** (re-predict repeatedly with the same fitted model) | a fairer real-time test |
| **IV** | Rolling window, **re-estimate β each step** | most realistic and most expensive; handles time-varying parameters |

Do **not** compare cross-validation scores across methods (apples to oranges). Cross-sectional validation (train/validation/test splits) assumes all signal comes from the same period, so it is not appropriate for time series.

**AI analogy** [S8]: valid inputs missing at inference (Method II) → worse predictions/hallucinations; inference with fixed weights ≈ Method III; refreshing a frontier model ≈ Method IV (costly).

---

## 14. Neural nets, LSTM, LLMs

[S9] Key ideas and how they relate to classical forecasting:
- **Neural networks are non-linear models**: layers apply `g(W·X + b)` with an activation function; deeper and wider nets approximate richer patterns and extract features automatically; trained via loss + optimiser + weight updates.
- **RNN**: a loop that reuses the previous state (like the transition equation of a state-space model) but suffers **vanishing/exploding gradients**, so it can't learn long dependencies.
- **LSTM**: adds a "carry track" (long memory) alongside the state (short memory); information can jump on and off, preventing older signals from vanishing. Analogue: ACF short vs long memory; the *forgetting factor* in dynamic model averaging.
- **LLMs**: autoregressive conditional probability `P(next token | history)`; trained by generative pre-training → supervised fine-tuning → RLHF.
- **Transformer**: multi-head attention lets every token look at all others in parallel (no step-by-step memory), which is much faster to train.

Practical stance: start from a baseline and a validated statistical model; reach for deep models when you have large volumes of data, non-linear patterns, or long dependencies, and validate them with the same out-of-sample discipline (§13).

---

## 15. Common pitfalls

- Regressing trending series on each other (spurious regression); fix with differences/growth rates or cointegration thinking. [S1, S5]
- Reading correlation as causation; ignoring confounders and reverse causality. [S1]
- Using a future X that you won't have in production (look-ahead bias). [S8]
- Overfitting with flexible models; judging only by in-sample fit. [S1, S2]
- Random train/test splits on time series. [S8]
- Forgetting seasonality or the SA/NSA distinction. [S3]
- Dummy-variable trap (k dummies plus intercept). [S3]
- Ignoring residual autocorrelation (use ARIMA errors or HAC standard errors). [S2, S5]
- Trusting automated library defaults for trend (Prophet). [S3]
- Ignoring structural breaks or changing parameters. [S8]
- Using a time-fixed-effect model for real-time forecasts. [S2]
- Using AI-generated code or answers unverified. [S1]

---

## 16. Model-choice cheat sheet

| Situation | Reach for |
|---|---|
| Long-run, smooth growth | linear/log-linear/logistic trend, Holt |
| Strong calendar pattern | seasonal dummies, SARIMA, seasonal plots |
| One stationary series with persistence | AR / ARMA (use PACF/ACF) |
| Trending / unit-root series | difference (ARIMA) or model growth rate |
| Known external drivers, future X known or scenario-based | structural / DL regression, ARIMAX |
| Drivers plus inertia, policy interpretation | ARDL / dynamic linear model |
| Variables influence each other | VAR (+ Granger, IRFs) |
| Dozens of correlated predictors | PCA → dynamic factor model; Lasso/Ridge |
| Parameters drift or breaks | Chow/sup-F tests, rolling windows, Kalman/state-space |
| Many entities over time | panel fixed/random effects, lags |
| Policy / intervention effect | RCT / A/B test, DID |
| Large non-linear data, long memory | NN, LSTM, Transformer |

---

## 17. Further reading

- Francis Diebold, free textbooks: *Elements of Forecasting*, *Econometric Data Science*, *Forecasting*, *Time Series Econometrics*. [S1]
- Hyndman & Athanasopoulos, *Forecasting: Principles and Practice*. [S1]
- Marco Peixeiro, *Time Series Forecasting in Python* (frequency tables, SARIMAX). [S1, S4, S5]
- Hansen (2001), "The New Econometrics of Structural Change"; Welch & Bishop, "An Introduction to the Kalman Filter"; Tusell (2011) and Petris & Petrone (2011) on Kalman filtering in R. [S8]
- Vaswani et al., "Attention Is All You Need" (2017). [S9]
