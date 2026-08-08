using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Threading;
using System.Windows.Forms;

internal static class ZhiYuLauncher
{
    [STAThread]
    private static int Main()
    {
        string root = AppDomain.CurrentDomain.BaseDirectory;
        string backend = Path.Combine(root, "runtime", "ZhiYuBackend.exe");
        string config = Path.Combine(root, ".env");
        if (!File.Exists(backend))
        {
            MessageBox.Show("运行组件缺失，请重新解压或安装智屿。", "智屿", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 2;
        }
        if (!File.Exists(config))
        {
            string example = Path.Combine(root, ".env.example");
            if (File.Exists(example)) File.Copy(example, config);
            MessageBox.Show("请先在配置文件中填写 PostgreSQL 密码和模型 API Key，保存后再次双击智屿。", "智屿首次配置", MessageBoxButtons.OK, MessageBoxIcon.Information);
            Process.Start(new ProcessStartInfo("notepad.exe", "\"" + config + "\"") { UseShellExecute = true });
            return 3;
        }

        if (!PortResponds("http://127.0.0.1:8001/api/v1/readyz"))
        {
            var info = new ProcessStartInfo(backend)
            {
                WorkingDirectory = Path.Combine(root, "runtime"),
                UseShellExecute = false,
                CreateNoWindow = true
            };
            info.EnvironmentVariables["ZHIXI_DESKTOP_OPEN_BROWSER"] = "false";
            try { Process.Start(info); }
            catch (Exception ex)
            {
                MessageBox.Show("启动失败：" + ex.Message, "智屿", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 4;
            }
            for (int i = 0; i < 120 && !PortResponds("http://127.0.0.1:8001/api/v1/readyz"); i++)
                Thread.Sleep(1000);
        }
        try { Process.Start(new ProcessStartInfo("http://127.0.0.1:8001") { UseShellExecute = true }); }
        catch { }
        return 0;
    }

    private static bool PortResponds(string url)
    {
        try
        {
            var request = (HttpWebRequest)WebRequest.Create(url);
            request.Timeout = 800;
            request.Method = "GET";
            using (var response = (HttpWebResponse)request.GetResponse())
                return (int)response.StatusCode < 500;
        }
        catch { return false; }
    }
}
