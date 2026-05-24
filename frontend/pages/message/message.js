// pages/message/message.js
const { request } = require('../../utils/api')

Page({
  data: {
    newMessage: '',
    messages: [],
    inputHeight: 40,
    loading: false,
  },

  onLoad() {
    this.loadMessages()
  },

  // ===== 從後端拉取留言 =====
  loadMessages() {
    const app = getApp()
    const memberId = app.globalData.userInfo && app.globalData.userInfo.member_id
    if (!memberId) {
      wx.showToast({ title: '請先登入', icon: 'none' })
      return
    }

    this.setData({ loading: true })
    request(`/api/feedback/?member_id=${memberId}`)
      .then(res => {
        if (res.success) {
          this.setData({ messages: res.messages })
        }
      })
      .catch(() => {
        wx.showToast({ title: '載入失敗', icon: 'none' })
      })
      .finally(() => {
        this.setData({ loading: false })
      })
  },

  onInput(e) {
    this.setData({ newMessage: e.detail.value })
  },

  onLineChange(e) {
    let physicalHeight = e.detail.height + 20
    if (physicalHeight > 90) physicalHeight = 90
    if (physicalHeight < 40) physicalHeight = 40
    this.setData({ inputHeight: physicalHeight })
  },

  // ===== 送出留言到後端 =====
  submitMessage() {
    const content = this.data.newMessage.trim()
    if (!content) {
      wx.showToast({ title: '内容不能為空', icon: 'none' })
      return
    }

    const app = getApp()
    const memberId = app.globalData.userInfo && app.globalData.userInfo.member_id
    if (!memberId) {
      wx.showToast({ title: '請先登入', icon: 'none' })
      return
    }

    request('/api/feedback/', 'POST', {
      member_id: memberId,
      message: content,
    })
      .then(res => {
        if (res.success) {
          // 把新留言插到列表最前面，不用重新拉取整個列表
          const newMsg = {
            id: res.id,
            content: res.content,
            time: res.time,
            reply: '',
            is_replied: false,
          }
          this.setData({
            messages: [newMsg, ...this.data.messages],
            newMessage: '',
            inputHeight: 40,
          })
          wx.showToast({ title: '發送成功', icon: 'success' })
        }
      })
      .catch(() => {
        wx.showToast({ title: '發送失敗，請稍後再試', icon: 'none' })
      })
  },
})
