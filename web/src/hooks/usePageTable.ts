/**
 * 分页表格：配合 nova-admin 的 <Pagination :count @change> 使用
 * load 返回后端 SuccessExtra（data + total），search 回到第 1 页
 */
export function usePageTable<T, Q extends Record<string, any>>(
  load: (params: Q & { page: number, page_size: number }) => PromiseLike<Service.PageResult<T>>,
  initialQuery: Q,
) {
  const loading = ref(false)
  const rows = ref<T[]>([]) as Ref<T[]>
  const total = ref(0)
  const query = ref({ ...initialQuery }) as Ref<Q>
  let page = 1
  let pageSize = 10

  async function fetch() {
    loading.value = true
    // 空条件不传：alova 会把 null 序列化成字符串 "null"
    const params = Object.fromEntries(Object.entries(query.value).filter(([, v]) => v !== null && v !== undefined && v !== '')) as Q
    const res = await load({ ...params, page, page_size: pageSize })
    loading.value = false
    if (res.isSuccess) {
      rows.value = res.data
      total.value = res.total
    }
  }

  function search() {
    page = 1
    return fetch()
  }

  function reset() {
    query.value = { ...initialQuery }
    return search()
  }

  function changePage(p: number, size: number) {
    page = p
    pageSize = size
    fetch()
  }

  onMounted(fetch)
  return { loading, rows, total, query, fetch, search, reset, changePage }
}
