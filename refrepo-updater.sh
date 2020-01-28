#!/bin/sh
# -*- mode: sh; tab-width: 4; indent-tabs-mode: nil; -*-

# -----------------------------------------------------------------------------
# Copyright (c) 2020 Marcus Geelnard
#
# This software is provided 'as-is', without any express or implied warranty.
# In no event will the authors be held liable for any damages arising from the
# use of this software.
#
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
#
#  1. The origin of this software must not be misrepresented; you must not
#     claim that you wrote the original software. If you use this software in
#     a product, an acknowledgment in the product documentation would be
#     appreciated but is not required.
#
#  2. Altered source versions must be plainly marked as such, and must not be
#     misrepresented as being the original software.
#
#  3. This notice may not be removed or altered from any source distribution.
# -----------------------------------------------------------------------------

# TODO(m): Make sure that the environment variables that we use are defined.

# Make sure that the configuration directory exists and is writable by all
# users.
mkdir -p "${REFREPO_ACE_ROOT_DIR}/${REFREPO_ACE_CONF_DIR}"
chmod go+ws "${REFREPO_ACE_ROOT_DIR}/${REFREPO_ACE_CONF_DIR}"

# Update the reference repository regularly.
while true; do
    echo "[$(date -Iseconds)] Updating: ${REFREPO_ACE_ROOT_DIR}/${REFREPO_ACE_REPO}"
    refrepo_ace.py

    sleep "${REFREPO_UPDATER_INTERVAL_SECONDS}"
done
