#! /usr/bin/env python3
# -*- coding: UTF-8 -*-

from dataclasses import dataclass
from typing import Literal, Any, Optional
import requests
import json

BASE_URL: str = 'https://api.crxcavator.io/v1/report'


@dataclass
class RiskDetail:
    ContentSecurityPolicy: str
    Permissions: str
    Webstore: str

    @staticmethod
    def parse(risk: Any) -> "RiskDetail":

        csp = risk.get('csp', {}).get('total', '')
        perms = risk.get('permissions', {}).get('total', '')
        ws = risk.get('webstore', {}).get('total', '')

        risk_detail = RiskDetail(
            ContentSecurityPolicy=csp,
            Permissions=perms,
            Webstore=ws)
        return risk_detail


@dataclass
class RiskReport:
    RiskScore: int
    RiskLevel: str
    Detail: RiskDetail

    @staticmethod
    def parse(response: Any) -> "RiskReport":
        risk: dict = response.get('data').get('risk')
        risk_score = int(risk.get('total', 0))
        if risk_score <= 377:
            risk_level = 'Low'
        elif risk_score > 377 and risk_score <= 478:
            risk_level = 'Medium'
        elif risk_score > 478:
            risk_level = 'High'
        else:
            risk_level = 'N/A'

        risk_detail: RiskDetail = RiskDetail.parse(risk)

        risk_score_detail = RiskReport(
            RiskScore=risk_score, RiskLevel=risk_level, Detail=risk_detail)
        return risk_score_detail


def get_risk_report(extension_id: str, extension_version: str, extension_platform: Literal['Firefox', 'Chrome', 'Edge']) -> Optional[RiskReport]:
    url: str = BASE_URL + '/' + extension_id + "/" + \
        extension_version + "?platform=" + extension_platform

    response: requests.Response = requests.get(url)
    if response.status_code == 200 and response.text != 'null\n':
        response_json: Any = json.loads(response.text)
        report: RiskReport = RiskReport.parse(response=response_json)
        return report

    return None
