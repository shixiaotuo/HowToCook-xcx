// 膳食偏好公共项：过敏原选项 + 忌口文本解析
module.exports = {
  ALLERGENS: ['鸡蛋', '牛奶', '花生', '坚果', '大豆', '小麦麸质', '鱼', '虾蟹甲壳类', '贝类'],
  parseDislikes(str) {
    return String(str || '')
      .split(/[,，\s]+/)
      .map((s) => s.trim())
      .filter(Boolean);
  },
};
