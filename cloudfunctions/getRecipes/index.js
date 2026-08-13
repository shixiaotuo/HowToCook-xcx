/**
 * CloudBase 云函数入口：getRecipes
 * 调用方式：wx.cloud.callFunction({ name: 'getRecipes', data: { action, ...params } })
 *
 * action 取值：
 *   getCategories      -> 返回分类列表与总数
 *   getAll             -> { category?, keyword?, page?, pageSize? } 全部菜谱简化版（分页）
 *   getByCategory      -> { category, keyword?, page?, pageSize? } 按分类获取
 *   recommendToday     -> { people, allergens?, dislikes? } 不知道吃什么
 *   recommendPlan      -> { people, allergens?, dislikes? } 一周膳食计划
 */
const { ACTIONS } = require('./logic');

exports.main = async (event = {}, context = {}) => {
  try {
    const { action } = event;
    if (!action || !ACTIONS[action]) {
      return { success: false, code: 'INVALID_ACTION', message: `未知 action: ${action}` };
    }
    const result = ACTIONS[action](event);
    return { success: true, action, data: result };
  } catch (err) {
    return { success: false, code: 'SERVER_ERROR', message: err.message };
  }
};
