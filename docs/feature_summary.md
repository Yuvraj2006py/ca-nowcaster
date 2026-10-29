# Feature summary

Owned by **Feature Engineer** (`src/nowcaster/features/`).

Index = target reference month. Features are built only from values
with `release_timestamp <= as_of_date` via `quality.as_of`.

Missing rates below are from a **Phase 2 synthetic vintage fixture** covering
all registry series (not live StatCan/BoC pulls). Re-run
`write_feature_summary` against the raw store for production rates.

- **as_of_date (for missing rates):** `2024-05-15`
- **features_hash:** `2ffacbb0782ff88f81bf4924eb12e8ea1fb8626951265092281f72af3f2d0fc1`
- **ragged_edge strategy:** `leave_missing`

## Feature table

| name | source | transform | lag | missing_rate | notes |
|---|---|---|---:|---:|---|
| `ca_gdp_basic_prices__mom_lag1` | `statcan:ca_gdp_basic_prices` | `mom` | 1 | 0.235 | Lagged target MoM only — contemporaneous target excluded |
| `ca_gdp_basic_prices__mom_lag2` | `statcan:ca_gdp_basic_prices` | `mom` | 2 | 0.235 | Lagged target MoM only — contemporaneous target excluded |
| `ca_gdp_basic_prices__mom_lag3` | `statcan:ca_gdp_basic_prices` | `mom` | 3 | 0.235 | Lagged target MoM only — contemporaneous target excluded |
| `ca_lfs_employment__mom` | `statcan:ca_lfs_employment` | `mom` | 0 | 0.118 | MoM % growth; lag months on growth series |
| `ca_lfs_employment__mom_lag1` | `statcan:ca_lfs_employment` | `mom` | 1 | 0.118 | MoM % growth; lag months on growth series |
| `ca_lfs_employment__mom_lag2` | `statcan:ca_lfs_employment` | `mom` | 2 | 0.176 | MoM % growth; lag months on growth series |
| `ca_lfs_employment__mom_lag3` | `statcan:ca_lfs_employment` | `mom` | 3 | 0.235 | MoM % growth; lag months on growth series |
| `ca_lfs_employment__yoy` | `statcan:ca_lfs_employment` | `yoy` | 0 | 0.765 | YoY % growth (needs 12 months of levels) |
| `ca_lfs_employment__logdiff` | `statcan:ca_lfs_employment` | `logdiff` | 0 | 0.118 | Δ log(level) |
| `ca_lfs_employment__rollmean3` | `statcan:ca_lfs_employment` | `rollmean3` | 0 | 0.176 | Trailing 3-month mean of levels |
| `ca_lfs_hours__mom` | `statcan:ca_lfs_hours` | `mom` | 0 | 0.118 | MoM % growth; lag months on growth series |
| `ca_lfs_hours__mom_lag1` | `statcan:ca_lfs_hours` | `mom` | 1 | 0.118 | MoM % growth; lag months on growth series |
| `ca_lfs_hours__mom_lag2` | `statcan:ca_lfs_hours` | `mom` | 2 | 0.176 | MoM % growth; lag months on growth series |
| `ca_lfs_hours__mom_lag3` | `statcan:ca_lfs_hours` | `mom` | 3 | 0.235 | MoM % growth; lag months on growth series |
| `ca_lfs_hours__yoy` | `statcan:ca_lfs_hours` | `yoy` | 0 | 0.765 | YoY % growth (needs 12 months of levels) |
| `ca_lfs_hours__logdiff` | `statcan:ca_lfs_hours` | `logdiff` | 0 | 0.118 | Δ log(level) |
| `ca_lfs_hours__rollmean3` | `statcan:ca_lfs_hours` | `rollmean3` | 0 | 0.176 | Trailing 3-month mean of levels |
| `ca_cpi_all_items__mom` | `statcan:ca_cpi_all_items` | `mom` | 0 | 0.118 | MoM % growth; lag months on growth series |
| `ca_cpi_all_items__mom_lag1` | `statcan:ca_cpi_all_items` | `mom` | 1 | 0.118 | MoM % growth; lag months on growth series |
| `ca_cpi_all_items__mom_lag2` | `statcan:ca_cpi_all_items` | `mom` | 2 | 0.176 | MoM % growth; lag months on growth series |
| `ca_cpi_all_items__mom_lag3` | `statcan:ca_cpi_all_items` | `mom` | 3 | 0.235 | MoM % growth; lag months on growth series |
| `ca_cpi_all_items__yoy` | `statcan:ca_cpi_all_items` | `yoy` | 0 | 0.765 | YoY % growth (needs 12 months of levels) |
| `ca_cpi_all_items__logdiff` | `statcan:ca_cpi_all_items` | `logdiff` | 0 | 0.118 | Δ log(level) |
| `ca_cpi_all_items__rollmean3` | `statcan:ca_cpi_all_items` | `rollmean3` | 0 | 0.176 | Trailing 3-month mean of levels |
| `ca_retail_sales__mom` | `statcan:ca_retail_sales` | `mom` | 0 | 0.118 | MoM % growth; lag months on growth series |
| `ca_retail_sales__mom_lag1` | `statcan:ca_retail_sales` | `mom` | 1 | 0.118 | MoM % growth; lag months on growth series |
| `ca_retail_sales__mom_lag2` | `statcan:ca_retail_sales` | `mom` | 2 | 0.176 | MoM % growth; lag months on growth series |
| `ca_retail_sales__mom_lag3` | `statcan:ca_retail_sales` | `mom` | 3 | 0.235 | MoM % growth; lag months on growth series |
| `ca_retail_sales__yoy` | `statcan:ca_retail_sales` | `yoy` | 0 | 0.765 | YoY % growth (needs 12 months of levels) |
| `ca_retail_sales__logdiff` | `statcan:ca_retail_sales` | `logdiff` | 0 | 0.118 | Δ log(level) |
| `ca_retail_sales__rollmean3` | `statcan:ca_retail_sales` | `rollmean3` | 0 | 0.176 | Trailing 3-month mean of levels |
| `ca_manufacturing_sales__mom` | `statcan:ca_manufacturing_sales` | `mom` | 0 | 0.118 | MoM % growth; lag months on growth series |
| `ca_manufacturing_sales__mom_lag1` | `statcan:ca_manufacturing_sales` | `mom` | 1 | 0.118 | MoM % growth; lag months on growth series |
| `ca_manufacturing_sales__mom_lag2` | `statcan:ca_manufacturing_sales` | `mom` | 2 | 0.176 | MoM % growth; lag months on growth series |
| `ca_manufacturing_sales__mom_lag3` | `statcan:ca_manufacturing_sales` | `mom` | 3 | 0.235 | MoM % growth; lag months on growth series |
| `ca_manufacturing_sales__yoy` | `statcan:ca_manufacturing_sales` | `yoy` | 0 | 0.765 | YoY % growth (needs 12 months of levels) |
| `ca_manufacturing_sales__logdiff` | `statcan:ca_manufacturing_sales` | `logdiff` | 0 | 0.118 | Δ log(level) |
| `ca_manufacturing_sales__rollmean3` | `statcan:ca_manufacturing_sales` | `rollmean3` | 0 | 0.176 | Trailing 3-month mean of levels |
| `ca_housing_starts__mom` | `statcan:ca_housing_starts` | `mom` | 0 | 0.118 | MoM % growth; lag months on growth series |
| `ca_housing_starts__mom_lag1` | `statcan:ca_housing_starts` | `mom` | 1 | 0.118 | MoM % growth; lag months on growth series |
| `ca_housing_starts__mom_lag2` | `statcan:ca_housing_starts` | `mom` | 2 | 0.176 | MoM % growth; lag months on growth series |
| `ca_housing_starts__mom_lag3` | `statcan:ca_housing_starts` | `mom` | 3 | 0.235 | MoM % growth; lag months on growth series |
| `ca_housing_starts__yoy` | `statcan:ca_housing_starts` | `yoy` | 0 | 0.765 | YoY % growth (needs 12 months of levels) |
| `ca_housing_starts__logdiff` | `statcan:ca_housing_starts` | `logdiff` | 0 | 0.118 | Δ log(level) |
| `ca_housing_starts__rollmean3` | `statcan:ca_housing_starts` | `rollmean3` | 0 | 0.176 | Trailing 3-month mean of levels |
| `boc_policy_rate__mom` | `boc_valet:boc_policy_rate` | `mom` | 0 | 0.118 | MoM % growth; lag months on growth series |
| `boc_policy_rate__mom_lag1` | `boc_valet:boc_policy_rate` | `mom` | 1 | 0.118 | MoM % growth; lag months on growth series |
| `boc_policy_rate__mom_lag2` | `boc_valet:boc_policy_rate` | `mom` | 2 | 0.176 | MoM % growth; lag months on growth series |
| `boc_policy_rate__mom_lag3` | `boc_valet:boc_policy_rate` | `mom` | 3 | 0.235 | MoM % growth; lag months on growth series |
| `boc_policy_rate__yoy` | `boc_valet:boc_policy_rate` | `yoy` | 0 | 0.765 | YoY % growth (needs 12 months of levels) |
| `boc_policy_rate__logdiff` | `boc_valet:boc_policy_rate` | `logdiff` | 0 | 0.118 | Δ log(level) |
| `boc_policy_rate__rollmean3` | `boc_valet:boc_policy_rate` | `rollmean3` | 0 | 0.176 | Trailing 3-month mean of levels |
| `boc_fx_usd_cad__mom` | `boc_valet:boc_fx_usd_cad` | `mom` | 0 | 0.176 | MoM % growth; lag months on growth series |
| `boc_fx_usd_cad__mom_lag1` | `boc_valet:boc_fx_usd_cad` | `mom` | 1 | 0.176 | MoM % growth; lag months on growth series |
| `boc_fx_usd_cad__mom_lag2` | `boc_valet:boc_fx_usd_cad` | `mom` | 2 | 0.176 | MoM % growth; lag months on growth series |
| `boc_fx_usd_cad__mom_lag3` | `boc_valet:boc_fx_usd_cad` | `mom` | 3 | 0.235 | MoM % growth; lag months on growth series |
| `boc_fx_usd_cad__yoy` | `boc_valet:boc_fx_usd_cad` | `yoy` | 0 | 0.824 | YoY % growth (needs 12 months of levels) |
| `boc_fx_usd_cad__logdiff` | `boc_valet:boc_fx_usd_cad` | `logdiff` | 0 | 0.176 | Δ log(level) |
| `boc_fx_usd_cad__rollmean3` | `boc_valet:boc_fx_usd_cad` | `rollmean3` | 0 | 0.235 | Trailing 3-month mean of levels |
| `boc_bcpi_total__mom` | `boc_valet:boc_bcpi_total` | `mom` | 0 | 0.176 | MoM % growth; lag months on growth series |
| `boc_bcpi_total__mom_lag1` | `boc_valet:boc_bcpi_total` | `mom` | 1 | 0.176 | MoM % growth; lag months on growth series |
| `boc_bcpi_total__mom_lag2` | `boc_valet:boc_bcpi_total` | `mom` | 2 | 0.176 | MoM % growth; lag months on growth series |
| `boc_bcpi_total__mom_lag3` | `boc_valet:boc_bcpi_total` | `mom` | 3 | 0.235 | MoM % growth; lag months on growth series |
| `boc_bcpi_total__yoy` | `boc_valet:boc_bcpi_total` | `yoy` | 0 | 0.824 | YoY % growth (needs 12 months of levels) |
| `boc_bcpi_total__logdiff` | `boc_valet:boc_bcpi_total` | `logdiff` | 0 | 0.176 | Δ log(level) |
| `boc_bcpi_total__rollmean3` | `boc_valet:boc_bcpi_total` | `rollmean3` | 0 | 0.235 | Trailing 3-month mean of levels |

## Ragged-edge strategies (v1)

| strategy | behavior |
|---|---|
| `leave_missing` | Trailing NaNs stay missing (models that support NaN / masking). |
| `carry` | Carry last published level into trailing months. |
| `ar1` | Simple AR(1) on level differences, then integrate forward. |

## How I could be wrong

- Missing rates depend on the as_of date and store contents; live rates
  will differ from fixture rates used in CI docs.
- YoY / rolling windows create structural leading NaNs unrelated to
  publication lag.
- AR(1) ragged fill is a crude imputer — not a structural nowcast.
