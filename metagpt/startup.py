#!/usr/bin/env python
# -*- coding: utf-8 -*-
# """
# @Time    : 2024/3/11 19:16
# @Author  : alexanderwu
# @File    : startup.py
# """

# DEPRECATED: This file is deprecated and will be removed in the future.
# The startup.py implementation has been moved to software_company.py
import asyncio
from metagpt.roles.flutter_developer import FlutterDeveloper
# from metagpt.roles.flutter_tester import FlutterTester
# from metagpt.roles.api_integrator import APIIntegrator
from metagpt.software_company import Company
async def main():
    company = Company()
    company.hire([
        FlutterDeveloper(),
        # APIIntegrator(),
        # FlutterTester()
    ])
    await company.run("Build a simple app that displays a list of products and allows users to add them to a cart.")

if __name__ == "__main__":
    asyncio.run(main())