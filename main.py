"""Chạy trọn bộ ABM: kịch bản A/B/C, sau đó phân tích nâng cao A/B/C/D.

Đặt file này ở thư mục gốc ABM_LaiSuat_Vu, cạnh src/, configs/, data/.
Chạy: python main.py
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_BANKS = Path('data/clean/abm_initial_8nganhang_2023Q1.csv')


def run_step(title: str, module: str, arguments: list[str]) -> None:
    command = [sys.executable, '-m', module, *arguments]
    print('\n' + '=' * 70, flush=True)
    print(title, flush=True)
    print('Lệnh:', subprocess.list2cmdline(command), flush=True)
    print('=' * 70, flush=True)
    subprocess.run(command, cwd=ROOT, check=True)
    print(f'HOÀN THÀNH: {title}', flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Chạy cả mô phỏng 3 kịch bản và phân tích nâng cao ABM.'
    )
    parser.add_argument('--config', type=Path, default=Path('configs/scenarios.yaml'),
                        help='YAML tham số (mặc định: configs/scenarios.yaml)')
    parser.add_argument('--banks', type=Path, default=DEFAULT_BANKS,
                        help='CSV khởi tạo ngân hàng (mặc định: Q1/2023)')
    parser.add_argument('--runs', type=int, default=60,
                        help='Số lần chạy cho mỗi kịch bản (mặc định: 60)')
    parser.add_argument('--sensitivity-runs', type=int, default=20,
                        help='Số lần chạy cho mỗi cấu hình độ nhạy nâng cao (mặc định: 20)')
    parser.add_argument('--panel', type=Path,
                        help='CSV panel lịch sử; nếu bỏ qua, advanced_analysis tự tìm file mặc định')
    parser.add_argument('--actual', type=Path,
                        help='CSV lãi suất thực tế month,loan_rate; ưu tiên thay cho panel')
    args = parser.parse_args()

    if args.runs < 1 or args.sensitivity_runs < 1:
        parser.error('--runs và --sensitivity-runs phải >= 1')

    # Đường dẫn tương đối được hiểu so với thư mục gốc dự án.
    def absolute(path: Path) -> Path:
        return path if path.is_absolute() else ROOT / path

    banks = absolute(args.banks)
    if not banks.is_file():
        parser.error(f'Không tìm thấy CSV ngân hàng: {banks}')

    for label, path in [('--panel', args.panel), ('--actual', args.actual)]:
        if path is not None and not absolute(path).is_file():
            parser.error(f'Không tìm thấy file {label}: {absolute(path)}')

    config = absolute(args.config)
    if not config.is_file():
        parser.error(f'Không tìm thấy file --config: {config}')

    common = ['--config', str(config), '--banks', str(banks), '--runs', str(args.runs)]
    advanced = [*common, '--sensitivity-runs', str(args.sensitivity_runs)]
    if args.panel is not None:
        advanced.extend(['--panel', str(absolute(args.panel))])
    if args.actual is not None:
        advanced.extend(['--actual', str(absolute(args.actual))])

    try:
        run_step('BƯỚC 1/2: Mô phỏng kịch bản A, B, C',
                 'src.analysis.experiments', common)
        run_step('BƯỚC 2/2: Phân tích nâng cao A, B, C, D và đối chiếu thực tế',
                 'src.analysis.advanced_analysis', advanced)
    except subprocess.CalledProcessError as error:
        print(f'\nDỪNG: Một chương trình báo lỗi (mã thoát {error.returncode}).',
              file=sys.stderr, flush=True)
        return error.returncode or 1

    print('\n' + '=' * 70, flush=True)
    print('HOÀN THÀNH CẢ HAI CHƯƠNG TRÌNH.', flush=True)
    print('Kiểm tra hai thư mục mới *_KichBan và *_PhanTichABC trong outputs/.',
          flush=True)
    print('=' * 70, flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
