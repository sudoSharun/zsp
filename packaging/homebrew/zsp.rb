# Homebrew formula for zsp.
#
# Lives in your tap repository (sudoSharun/homebrew-tap) as
# Formula/zsp.rb — not in this repo's checkout. Kept here so the formula is
# version-controlled alongside the code it installs.
#
# Refresh on release:
#   1. Bump `url` to the new PyPI sdist
#   2. shasum -a 256 zsp-<version>.tar.gz  → update `sha256`
#   3. Commit to the tap repo
#
# There are no Python dependencies to vendor — the package is stdlib only,
# which is why this formula has no `resource` blocks.

class Zsp < Formula
  include Language::Python::Virtualenv

  desc "Command-line client for Zoho Sprints"
  homepage "https://github.com/sudoSharun/zsp"
  url "https://files.pythonhosted.org/packages/source/z/zsp/zsp-0.1.0.tar.gz"
  sha256 "REPLACE_WITH_SDIST_SHA256"
  license "MIT"
  head "https://github.com/sudoSharun/zsp.git", branch: "main"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "zsp #{version}", shell_output("#{bin}/zsp --version")

    # Without credentials the CLI must fail cleanly, not stack-trace.
    output = shell_output("#{bin}/zsp projects 2>&1", 3)
    assert_match "zsp login", output
  end
end
