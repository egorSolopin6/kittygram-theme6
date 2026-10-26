from showcase.views import CatViewSet

# Legacy route uses exactly the same permissions and pagination as /api/cats/.
cat_list = CatViewSet.as_view({'get': 'list', 'post': 'create'})
