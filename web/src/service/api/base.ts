import { request } from '../http'

/** 当前用户（控制台本地用户） */
export function fetchUserInfo() {
  return request.Get<Service.ResponseResult<Api.Login.Info>>('/base/userinfo')
}

/** 当前用户可见菜单（树） */
export function fetchUserMenus() {
  return request.Get<Service.ResponseResult<Entity.Menu[]>>('/base/usermenu')
}

/** 当前用户的接口权限码：method + path，如 post/api/v1/role/create */
export function fetchUserApis() {
  return request.Get<Service.ResponseResult<string[]>>('/base/userapi')
}

/** 修改密码：由认证模块完成 */
export function fetchUpdatePassword(data: { old_password: string, new_password: string }) {
  return request.Post<Service.ResponseResult<null>>('/base/update_password', data)
}

/** 上传当前用户头像 */
export function fetchUploadAvatar(data: FormData) {
  return request.Post<Service.ResponseResult<{ avatar: string }>>('/base/avatar', data)
}
