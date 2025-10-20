from task.BaseTask import BaseTask
from typing import Any, Dict, List
import colorsys
import psutil

HLS_SATURATION = 0.5
HLS_LIGHTNESS = 0.5

"""
Outputs system resources information (CPU, RAM, Swap, Disk, Processes).
"""
class SystemMonitor(BaseTask):
    def run(self, carry: Dict[str, Any]) -> Dict[str, Any]:
        self._print(f"SystemMonitor")
        system = {
            "cpu": self._get_cpu(),
            "memory": self._get_ram(),
            "swap": self._get_swap(),
            "disk": self._get_disk(),
            "processes": self._get_processes(),
        }
        self._print(f"SystemMonitor: cpu %.2f%%, memory %.1f/%.1f GB" % (
            system['cpu']['usage_percent'],
            system['memory']['total_gb'] - system['memory']['available_gb'],
            system['memory']['total_gb']
        ))
        return system

    def text_output(self, data: Dict[str, Any]) -> str:
        ram_total = float(data['memory']['total_gb'])
        ram_available = float(data['memory']['available_gb'])
        ram_used = ram_total - ram_available
        return "cpu %.2f%%, memory %.1f/%.1f GB" % (
            data['cpu']['usage_percent'],
            ram_used,
            ram_total,
        )

    def html_output(self, data: Dict[str, Any]) -> str:
        cpu_percent = float(data['cpu']['usage_percent'])
        per_core = data['cpu'].get('per_core_percent', [])
        ram_total = float(data['memory']['total_gb'])
        ram_available = float(data['memory']['available_gb'])
        ram_used = ram_total - ram_available
        ram_percent = float(data['memory']['used_percent'])
        disk_percent = float(data['disk'].get('used_percent', 0.0))
        swap_total = float(data['swap'].get('total_gb', 0.0))
        swap_used = float(data['swap'].get('used_gb', 0.0))
        swap_percent = float(data['swap'].get('used_percent', 0.0))
        foreground_colors = self._rainbow_colors(64)
        progress_bar_core_list = []
        for idx, val in enumerate(per_core):
            progress_bar_core_list.append(
                self._render_html_from_template('template/SystemMonitorProgressBarCore.html', {
                    'foreground_color': foreground_colors[idx % len(foreground_colors)],
                    'background_color': '#2b2b2b',
                    'height': '8px',
                    'usage': f"%.0f" % (val),
                })
            )
        progress_bar_cores = "\n".join(progress_bar_core_list)
        progress_bar_cpu = self._render_html_from_template('template/SystemMonitorProgressBar.html', {
            'foreground_color': '#4caf50',
            'background_color': '#2b2b2b',
            'height': '16px',
            'usage': f"%.0f" % (cpu_percent),
        })
        progress_bar_ram = self._render_html_from_template('template/SystemMonitorProgressBar.html', {
            'foreground_color': '#2196f3',
            'background_color': '#2b2b2b',
            'height': '16px',
            'usage': f"%.0f" % (ram_percent),
        })
        progress_bar_swap = self._render_html_from_template('template/SystemMonitorProgressBar.html', {
            'foreground_color': '#9c27b0',
            'background_color': '#2b2b2b',
            'height': '16px',
            'usage': f"%.0f" % (swap_percent),
        })
        progress_bar_disk = self._render_html_from_template('template/SystemMonitorProgressBar.html', {
            'foreground_color': '#ff9800',
            'background_color': '#2b2b2b',
            'height': '16px',
            'usage': f"%.0f" % (disk_percent),
        })
        # Build processes table
        proc_rows: List[str] = []
        for proc in data.get('processes', []):
            pid = str(proc.get('pid', ''))
            name = str(proc.get('name', ''))
            cpu = float(proc.get('cpu_percent', 0.0))
            proc_rows.append(
                self._render_html_from_template('template/SystemMonitorProcessRow.html', {
                    'pid': pid,
                    'name': name,
                    'cpu_percent': f"{cpu:.1f}",
                })
            )
        processes_list = self._render_html_from_template('template/SystemMonitorProcessList.html', {
            'processes': "\n".join(proc_rows),
        })
        html = self._render_html_from_template('template/SystemMonitor.html', {
            'progress_bar_cpu': progress_bar_cpu,
            'progress_bar_ram': progress_bar_ram,
            'progress_bar_swap': progress_bar_swap,
            'progress_bar_disk': progress_bar_disk,
            'progress_bar_cores': progress_bar_cores,
            'cpu_percent': "%.2f%%" % (cpu_percent),
            'ram_percent': "%.2f%%" % (ram_percent),
            'swap_percent': "%.2f%%" % (swap_percent),
            'disk_percent': "%.2f%%" % (disk_percent),
            'ram_used': "%.1f" % (ram_used),
            'ram_total': "%.1f" % (ram_total),
            'swap_used': "%.1f" % (swap_used),
            'swap_total': "%.1f" % (swap_total),
            'processes_list': processes_list,
        })
        return html

    def interval(self) -> int:
        return 5

    def name(self) -> str:
        return "system_monitor"

    def dependencies(self) -> Dict[str, Any]:
        return {'pip': ['psutil']}

    def _get_cpu(self) -> Dict[str, Any]:
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)
        return {
            "usage_percent": cpu_percent,
            "per_core_percent": cpu_per_core,
        }

    def _get_ram(self) -> Dict[str, Any]:
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "used_percent": mem.percent,
        }

    def _get_swap(self) -> Dict[str, Any]:
        swap = psutil.swap_memory()
        return {
            "total_gb": round(swap.total / (1024**3), 2),
            "used_gb": round(swap.used / (1024**3), 2),
            "used_percent": swap.percent,
        }

    def _get_disk(self) -> Dict[str, Any]:
        disk = psutil.disk_usage('/')
        return {
            "used_percent": disk.percent,
        }

    def _get_processes(self) -> List[Dict[str, Any]]:
        processes: List[Dict[str, Any]] = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            processes.append(proc.info)
        return processes

    def _rainbow_colors(self, n: int = 64) -> List[str]:
        colors = []
        for i in range(n):
            h = (i / n) % 1.0
            s = HLS_SATURATION
            l = HLS_LIGHTNESS
            r, g, b = colorsys.hls_to_rgb(h, l, s)
            colors.append('#%02x%02x%02x' % (int(r * 255), int(g * 255), int(b * 255)))
        return colors
