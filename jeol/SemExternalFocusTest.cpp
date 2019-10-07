//	////////////////////////////////////////////////////////////////////
//  Test based on "SemExternalSample.cpp" by JEOL.
//  Modified by Frank Vernaillen, VIB, Oct 2019
//
//  Building .exe:
//  1. Open a "VS2015 x86 Native Tools Command Prompt"
//     Note that it must be an x86, NOT x64 prompt because we need
//     to build a 32-bit executable, since we need to link to the 32-bit SemExternal.dll.
//  2. cl SemExternalFocusTest.cpp
//     This builds SemExternalFocusTest.exe
//	////////////////////////////////////////////////////////////////////

#include <stdio.h>
#include <tchar.h>
#include <windows.h>

// Include BasicPackage.h
#include "BasicPackage.h"

typedef BOOL ( *SEM_EXTERNAL_INIT_DLL)(HINSTANCE hAppInstance, BOOL bUnused);
typedef BOOL ( *SEM_EXTERNAL_TERM_DLL)(HINSTANCE hAppInstance);
typedef void* ( *SEM_EXTERNAL_SOCKET_OPEN)();
typedef long ( *SEM_EXTERNAL_SOCKET_CLOSE)();
typedef long ( *SEM_EXTERNAL_CONNECT)();
typedef long ( *SEM_EXTERNAL_DISCONNECT)();

typedef long ( *SEM_EXTERNAL_SET_MAG)(unsigned long ulMag);
typedef long ( *SEM_EXTERNAL_GET_MAG)(unsigned long* ulMag);

typedef long ( *SEM_EXTERNAL_SET_FOCUS)(short focus);
typedef long ( *SEM_EXTERNAL_GET_FOCUS)(short *focus);

typedef long ( *SEM_EXTERNAL_SET_STAGE_MOVE)(STAGE_SET_POS stagePosSet);
typedef long ( *SEM_EXTERNAL_GET_STAGE_CONFIG)(STAGE_CONFIG *stageConfigCurrent);


int _tmain(int argc, _TCHAR* argv[])
{
	// Initialize
	HINSTANCE hDLL = 0;
	SEM_EXTERNAL_INIT_DLL pFuncInitDll = 0;
	SEM_EXTERNAL_TERM_DLL pFuncTermDll = 0;
	SEM_EXTERNAL_SOCKET_OPEN pFuncSocketOpen = 0;
	SEM_EXTERNAL_SOCKET_CLOSE pFuncSocketClose = 0;
	SEM_EXTERNAL_CONNECT pFuncConnect = 0;
	SEM_EXTERNAL_DISCONNECT pFuncDisconnect = 0;

	SEM_EXTERNAL_SET_MAG pFuncSetMag = 0;
	SEM_EXTERNAL_GET_MAG pFuncGetMag = 0;

	SEM_EXTERNAL_SET_FOCUS pFuncSetFocus = 0;
	SEM_EXTERNAL_GET_FOCUS pFuncGetFocus = 0;

	SEM_EXTERNAL_SET_STAGE_MOVE pFuncSetStageMove = 0;
	SEM_EXTERNAL_GET_STAGE_CONFIG pFuncGetStageConfig = 0;


	printf("Loading SemExternal.dll.\n");
	hDLL = LoadLibrary(_T("SemExternal.dll"));
	if (0 == hDLL)
	{
		// Load library error
		printf("SemExternal.dll: Load library error.\n");
		system("PAUSE");
		return 1;
	}

	// Load function pointer
	printf("Geting function pointers from SemExternal.dll.\n");
	pFuncInitDll = (SEM_EXTERNAL_INIT_DLL)GetProcAddress(hDLL, "eikInitDLL");
	pFuncTermDll = (SEM_EXTERNAL_TERM_DLL)GetProcAddress(hDLL, "eikTermDLL");
	pFuncSocketOpen = (SEM_EXTERNAL_SOCKET_OPEN)GetProcAddress(hDLL, "eikSocketOpen");
	pFuncSocketClose = (SEM_EXTERNAL_SOCKET_CLOSE)GetProcAddress(hDLL, "eikSocketClose");
	pFuncConnect = (SEM_EXTERNAL_CONNECT)GetProcAddress(hDLL, "eikSocketConnect");
	pFuncDisconnect = (SEM_EXTERNAL_DISCONNECT)GetProcAddress(hDLL, "eikSocketDisconnect");
	
	pFuncSetMag = (SEM_EXTERNAL_SET_MAG)GetProcAddress(hDLL, "eikSetMag");
	pFuncGetMag = (SEM_EXTERNAL_GET_MAG)GetProcAddress(hDLL, "eikGetMag");

	pFuncSetFocus = (SEM_EXTERNAL_SET_FOCUS)GetProcAddress(hDLL, "eikSetAclCorrect");
	pFuncGetFocus = (SEM_EXTERNAL_GET_FOCUS)GetProcAddress(hDLL, "eikGetAclCorrect");

	pFuncSetStageMove = (SEM_EXTERNAL_SET_STAGE_MOVE)GetProcAddress(hDLL, "eikSetStageMove");
	pFuncGetStageConfig = (SEM_EXTERNAL_GET_STAGE_CONFIG)GetProcAddress(hDLL, "eikGetStageConfig");


	if ( (0 == pFuncInitDll) || (0 == pFuncTermDll) || (0 == pFuncSocketOpen)
		|| (0 == pFuncSocketClose) || (0 == pFuncConnect) || (0 == pFuncDisconnect)
		|| (0 == pFuncSetMag) || (0 == pFuncSetStageMove) || (0 == pFuncGetStageConfig)
		|| (0 == pFuncGetMag) || (0 == pFuncGetFocus) || (0 == pFuncSetFocus))
	{
		// Load function pointer error
		printf("Geting function pointers failed.\n");
		if (0 == FreeLibrary(hDLL))
		{
			printf("Free library error.\n");
		}
		system("PAUSE");
		return 1;
	}

	printf("eikInitDLL\n");
	if (TRUE != pFuncInitDll(GetModuleHandle(0), 0))
	{
		printf("eikInitDLL: failed.\n");
		if (0 == FreeLibrary(hDLL))
		{
			printf("Free library error.\n");
		}
		system("PAUSE");
		return 1;
	}

	// Connect
	printf("eikSocketOpen.\n");
	void* pvResult = 0;
	pvResult = pFuncSocketOpen();
	if (0 == pvResult)
	{
		// Socket open error
		printf("eikSocketOpen error.\n");
		if (0 == FreeLibrary(hDLL))
		{
			printf("Free library error.\n");
		}
		system("PAUSE");
		return 1;
	}

	printf("eikSocketConnect.\n");
	bool bConnectFlag = false;
	if ( 0 == pFuncConnect() )
	{
		bConnectFlag = true;
	}
	else
	{
		// Socket connect error
		printf("eikSocketConnect error.\n");
	}

	if (true == bConnectFlag)
	{
		printf("eikSetMag: set magnification to 2000.\n");
		if (0 != pFuncSetMag(2000))
		{
			printf("Set magnification error.\n");
		}
		else
		{
			printf("Set magnification successful");
		}

		printf("eikGetMag: get magnification.\n");
		unsigned long mag = 0;
		if (0 != pFuncGetMag(&mag))
		{
			printf("Get magnification error.\n");
		}
		else
		{
			printf("Magnification is %d\n", mag);
		}
		system("PAUSE");

		printf("eikGetAclCorrect: get focus.\n");
		short focus = 999;
		if (0 != pFuncGetFocus(&focus))
		{
			printf("Get focus error.\n");
		}
		else
		{
			printf("Focus is %d\n", focus);
		}

		printf("eikSetAclCorrect: set focus to -24 (whatever that means...).\n");
		if (0 != pFuncSetFocus(-24))
		{
			printf("Set focus error.\n");
		}
		else
		{
			printf("Set focus successful.\n");
		}

		printf("eikGetAclCorrect: get focus.\n");
		focus = 999;
		if (0 != pFuncGetFocus(&focus))
		{
			printf("Get focus error.\n");
		}
		else
		{
			printf("Focus is %d\n", focus);
		}
		system("PAUSE");

		printf("eikSetAclCorrect: set focus to +2 (whatever that means...).\n");
		if (0 != pFuncSetFocus(2))
		{
			printf("Set focus error.\n");
		}
		else
		{
			printf("Set focus successful.\n");
		}

		printf("eikGetAclCorrect: get focus.\n");
		focus = 999;
		if (0 != pFuncGetFocus(&focus))
		{
			printf("Get focus error.\n");
		}
		else
		{
			printf("Focus is %d\n", focus);
		}
		system("PAUSE");


		// Get stage config
//		printf("Get stage config.\n");
//		STAGE_CONFIG stageConfig={0};
//		if (0 == pFuncGetStageConfig(&stageConfig))
//		{
//			// Successful get stage config
//
//			// Set stage move(move to X=10.0, R=5.0)
//			printf("Set stage move.\n");
//			STAGE_SET_POS stageSetPos={0};
//			stageSetPos.set_abs=1;
//			stageSetPos.axis_move[stageConfig.x_axis]=1;
//			stageSetPos.axis_move[stageConfig.r_axis]=1;
//			stageSetPos.axis_pos[stageConfig.x_axis]=10.0f;
//			stageSetPos.axis_pos[stageConfig.r_axis]=5.0f;
//
//			if (0 != pFuncSetStageMove(stageSetPos))
//			{
//				// Stage move error
//				printf("Stage move error.\n");
//			}
//		}
//		else
//		{
//			// Get stage config error
//			printf("Get stage config error.\n");
//		}

	}

	// Disconnect
	if (true == bConnectFlag)
	{
		printf("eikSocketDisconnect.\n");
		if (0 == pFuncDisconnect())
		{
			bConnectFlag = false;
		}
		else
		{
			// Disconnect error
			printf("Socket disconnect error.\n");
		}
	}

	// Terminate
	printf("eikSocketClose.\n");
	if (0 > pFuncSocketClose())
	{
		// Socket close error
		printf("Socket close error.\n");
	}
	printf("eikTermDLL.\n");
	if (FALSE == pFuncTermDll(GetModuleHandle(0)))
	{
		// Term DLL error
		printf("eikTermDLL error.\n");
	}
	printf("Free library.\n");
	if (0 == FreeLibrary(hDLL))
	{
		printf("Free library error.\n");
	}

	system("PAUSE");
	return 0;
}
