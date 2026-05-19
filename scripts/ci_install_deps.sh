#!/bin/sh
# Install Python deps in GitLab CI. Shared K8s runners usually reach PyPI.org
# faster than Iranian mirrors; Liara is used as fallback for local/docker builds.
set -eu

unset PIP_INDEX_URL PIP_TRUSTED_HOST PIP_EXTRA_INDEX_URL || true
export PIP_CONFIG_FILE=/dev/null
export PIP_DISABLE_PIP_VERSION_CHECK=1

pip_install() {
  index="$1"
  trusted="$2"
  echo ">>> pip install -i ${index}"
  python -m pip install \
    --default-timeout=180 \
    --retries 3 \
    --trusted-host "${trusted}" \
    -i "${index}" \
    -r requirements.txt
}

if pip_install "https://pypi.org/simple" "pypi.org files.pythonhosted.org"; then
  echo ">>> dependencies installed from PyPI.org"
  exit 0
fi

echo ">>> PyPI.org failed, trying Liara mirror..."
pip_install "https://package-mirror.liara.ir/repository/pypi/simple" "package-mirror.liara.ir"
echo ">>> dependencies installed from Liara"
