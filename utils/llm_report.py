def generate_report(matches, missing):
    report = []
    for m in matches:
        report.append( f"{m['req']} 요구사항이 구현 코드와 정합성을 보였습니다." )

    for miss in missing:
        report.append( f"{miss} 요구사항은 구현이 누락되었습니다." )

    return report
