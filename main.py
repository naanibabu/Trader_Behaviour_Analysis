"""Run the complete data preparation and PDF reporting workflow."""

from pathlib import Path


def main() -> list[Path]:
    from transforme_df import df
    from univarient_analysis_report import create_univariate_analysis_report
    from bivarient_analysis_report import create_bivariate_analysis_report
    from multivarient_analysis_report import create_multivariate_analysis_report

    reports_directory = Path(__file__).resolve().parent / "reports"
    reports_directory.mkdir(parents=True, exist_ok=True)

    reports = [
        create_univariate_analysis_report(df, reports_directory),
        create_bivariate_analysis_report(df, reports_directory),
        create_multivariate_analysis_report(df, reports_directory),
    ]

    for report_path in reports:
        print(f"Created report: {report_path}")

    return reports


if __name__ == "__main__":
    main()