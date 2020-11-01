#! /usr/bin/env python
# -*- coding:utf-8 -*-

import configparser


class GenConfig:
	"""配置文件(通用)读取接口"""
	def __init__ (self, 
		cfgFile,	#配置文件
		):
		self.config = configparser.ConfigParser()
		self.config.read(cfgFile)
		self.cfgFile = cfgFile
	
	#返回配置段列表
	def sectionList (self):
		return self.config.sections()
	
	#返回选项值
	def getSecOption (self, 
		section,	#配置段
		option,		#配置选项
		):
		try:
			optVal = self.config.get(section, option)
			return optVal
		except Exception:
			return None

	#设置选项值
	def setSecOption (self, 
		section,	#配置段
		option,		#配置选项
		value,		#值
		):
		try:
			self.config.set(section, option, value)
			self.config.write(open(self.cfgFile, "w"))
			return True
		except Exception:
			return False
	
	#添加配置段
	def addSection (self, 
		section,	#配置段
		):
		try:
			self.config.add_section(section)
			self.config.write(open(self.cfgFile, "w"))
			return True
		except Exception:
			return False

	#删除配置段
	def removeSection (self, 
		section,	#配置段
		):
		try:
			self.config.remove_section(section)
			self.config.write(open(self.cfgFile, "w"))
			return True
		except Exception:
			return False
	
	#删除选项值
	def removeOption (self, 
		section,	#配置段
		option,		#配置选项
		):
		try:
			self.config.remove_option(section, option)
			self.config.write(open(self.cfgFile, "w"))
			return True
		except Exception:
			return False

#测试
def doTest():
	gc = GenConfig("test_gencfg")
	gc.addSection('COMMAND')
	gc.addSection('75UABKHBFFA5')
	gc.addSection('71MBBLC22R4H')
	
	gc.setSecOption('COMMAND', 'command', './mztest.py runtest -u -D -s rtc')
	
	gc.setSecOption('75UABKHBFFA5', 'start', 'Mon May 25 17:28:17 CST 2015')
	gc.setSecOption('75UABKHBFFA5', 'end', 'Mon May 25 21:28:17 CST 2015')
	gc.setSecOption('75UABKHBFFA5', 'duration', '5 hours')
	
	gc.setSecOption('71MBBLC22R4H', 'start', 'Mon May 25 17:28:30 CST 2015')
	gc.setSecOption('71MBBLC22R4H', 'end', 'Mon May 25 18:28:17 CST 2015')
	gc.setSecOption('75UABKHBFFA5', 'duration', '1 hours')
	
	gc.addSection('COMMAND_TEST1')
	gc.removeSection('71MBBLC22R4H')
	gc.removeOption('75UABKHBFFA5', 'duration')
	
	print(gc.sectionList())
	
	#测试结果
	'''
	[COMMAND]
	command = ./mztest.py runtest -u -D -s rtc
	
	[75UABKHBFFA5]
	start = Mon May 25 17:28:17 CST 2015
	end = Mon May 25 21:28:17 CST 2015
	
	[COMMAND_TEST1]
	'''

if __name__ == '__main__':
	doTest()
