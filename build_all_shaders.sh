#!/usr/bin/env bash
# Build all shaders for all platforms.
# Usage: ./build_all_shaders.sh <output-dir>

# /*
# (c) 2026 Eduardo Doria.
# */

set -euo pipefail

EDITOR="${DORIAX_EDITOR:-./build/doriax-editor}"
OUT="${1:?Usage: $0 <output-dir>}"

exec "$EDITOR" shaders \
  --out "$OUT" \
  --format header \
  --shader mesh:Uv1,Puc,Nor,Nmp,Tan,Vc4 \
  --shader mesh:Uv1,Puc,Nor,Nmp,Tan,Vc4,Fog \
  --shader mesh:Uv1,Puc,Nor,Nmp,Tan,Vc4,Ski \
  --shader mesh:Uv1,Puc,Nor,Nmp,Tan,Vc4,Fog,Ski \
  --shader mesh:Uv1,Puc,Nor,Nmp,Tan \
  --shader mesh:Uv1,Puc,Nor,Nmp,Tan,Fog \
  --shader mesh:Uv1,Puc,Shw,Nor,Nmp,Tan,Vc4 \
  --shader mesh:Uv1,Puc,Shw,Nor,Nmp,Tan,Vc4,Fog \
  --shader mesh:Uv1,Puc,Shw,Nor,Nmp,Tan \
  --shader mesh:Uv1,Puc,Shw,Nor,Nmp,Tan,Fog \
  --shader mesh:Uv1,Puc,Nor,Vc4 \
  --shader mesh:Uv1,Puc,Nor,Vc4,Fog \
  --shader mesh:Uv1,Puc,Nor \
  --shader mesh:Uv1,Puc,Nor,Fog \
  --shader mesh:Uv1,Puc,Nor,Vc4,Txr \
  --shader mesh:Uv1,Puc,Nor,Vc4,Txr,Ist \
  --shader mesh:Uv1,Puc,Nor,Vc4,Ist \
  --shader mesh:Uv1,Puc,Shw,Nor,Vc4 \
  --shader mesh:Uv1,Puc,Shw,Nor,Vc4,Ist \
  --shader mesh:Uv1,Puc,Shw,Nor,Vc4,Fog \
  --shader mesh:Uv1,Puc,Shw,Nor,Vc4,Txr \
  --shader mesh:Uv1,Puc,Shw,Nor,Vc4,Fog,Ist \
  --shader mesh:Uv1,Puc,Shw,Nor,Vc4,Txr,Ist \
  --shader mesh:Uv1,Puc,Shw,Nor \
  --shader mesh:Uv1,Puc,Shw,Nor,Ski \
  --shader mesh:Uv1,Puc,Shw,Nor,Ski,Ist \
  --shader mesh:Uv1,Puc,Shw,Nor,Nmp,Vc4 \
  --shader mesh:Uv1,Puc,Shw,Nor,Fog \
  --shader mesh:Uv1,Puc,Shw,Nor,Fog,Ist \
  --shader mesh:Uv1,Puc,Shw,Nor,Fog,Ski \
  --shader mesh:Ult,Uv1,Vc4 \
  --shader mesh:Ult,Uv1,Vc4,Fog \
  --shader mesh:Ult \
  --shader mesh:Ult,Uv1 \
  --shader mesh:Ult,Vc4 \
  --shader mesh:Uv1,Puc,Nor,Ter \
  --shader mesh:Uv1,Puc,Shw,Nor,Ter \
  --shader mesh:Uv1,Puc,Shw,Nor,Fog,Ter \
  --shader mesh:Ult,Uv1,Ter \
  --shader mesh:Ult,Ski \
  --shader mesh:Ult,Uv1,Fog \
  --shader mesh:Ult,Uv1,Ski \
  --shader mesh:Ult,Vc4,Ski \
  --shader mesh:Ult,Uv1,Vc4,Ist \
  --shader mesh:Ult,Uv1,Vc4,Txr \
  --shader mesh:Ult,Uv1,Vc4,Txr,Ist \
  --shader mesh:Ult,Uv1,Vc4,Txr,Fog \
  --shader mesh:Ult,Mta,Mnr,Mtg \
  --shader mesh:Puc,Nor,Vc4,Ski \
  --shader mesh:Puc,Shw,Nor \
  --shader mesh:Puc,Shw,Nor,Ski \
  --shader mesh:Puc,Shw,Nor,Fog \
  --shader mesh:Puc,Shw,Nor,Fog,Ski \
  --shader mesh:Puc,Shw,Nor,Vc4 \
  --shader mesh:Puc,Shw,Nor,Vc4,Ski \
  --shader mesh:Puc,Shw,Nor,Vc4,Fog \
  --shader mesh:Puc,Shw,Nor,Vc4,Ist \
  --shader mesh:Puc,Shw,Nor,Vc4,Fog,Ski \
  --shader mesh:Ult,Uv1,Nor,Tan,Vc4,Txr,L2d,S2d \
  --shader mesh:Puc,Shw,Nor,Tan,Mta,Mnr \
  --shader mesh:Puc,Shw,Nor,Tan,Mta,Mnr,Mtg \
  --shader mesh:Puc,Shw,Nor,Tan,Fog,Mta,Mnr \
  --shader mesh:Puc,Shw,Nor,Tan,Fog,Mta,Mnr,Mtg \
  --shader depth \
  --shader depth:Tex \
  --shader depth:Tex,Ist \
  --shader depth:Ski \
  --shader depth:Mta \
  --shader depth:Mta,Mnr \
  --shader depth:Mta,Mnr,Mtg \
  --shader depth:Ist \
  --shader depth:Ski,Ist \
  --shader depth:Mta,Ist \
  --shader depth:Mta,Mnr,Ist \
  --shader depth:Mta,Mnr,Mtg,Ist \
  --shader depth:Ter \
  --shader shadow2d \
  --shader sky \
  --shader ui:Vc4 \
  --shader ui:Tex,Vc4 \
  --shader ui:Ftx \
  --shader points:Vc4 \
  --shader points:Tex,Vc4 \
  --shader points:Tex,Vc4,Txr \
  --shader lines:Vc4
