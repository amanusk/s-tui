class STui < Formula
  desc "Stress Terminal UI stress test and monitoring tool"
  homepage "https://github.com/amanusk/s-tui"
  url "https://pypi.io/packages/source/s/s-tui/s-tui-1.1.5.tar.gz"
  sha256 "91656828859942699c27931c19793132646296998634567280b2a74653457112"
  license "GPL-2.0-or-later"

  depends_on "python"

  def install
    virtualenv_install_with_resources
  end

  test do
    # Test that the s-tui command runs and shows its version
    assert_match version.to_s, shell_output("#{bin}/s-tui --version")

    # Test a non-interactive run with JSON output and debug-run flag.
    # debug-run ensures it runs one loop and exits, suitable for testing.
    # The output should be a JSON object.
    assert_match /^{.*}$/, shell_output("#{bin}/s-tui --json --debug-run")
  end
end
