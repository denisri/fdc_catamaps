console.log('service sw.js');

// Files to cache
const my_path = location.pathname.replace('/sw.js', '');
var s = my_path.split('/');
const par_path = my_path.substring(0,
                                   my_path.length - s[s.length - 1].length);
const mapname = s[s.length - 1];
console.log('mapname:', mapname);
var version;
var cacheName;
var map_objects;

const appShellFiles = [
  my_path + '/help.html',
  my_path + '/index.html',
  my_path + '/map_objects.json',
  my_path + '/compass/',
  my_path + '/jquery.js',
  my_path + '/meshes_obj/',
  my_path + '/OrbitControls2.js',
  my_path + '/catamap_icon.jpg',
  my_path + '/catamap.webmanifest',
  my_path + '/photos/',
  my_path + '/sounds/',
  par_path + '/three/',
];


async function wait_json()
{
  console.log('wait_json');
  const map_objects = await fetch('map_objects.json').then((response) => response.json());

  return map_objects;
}


function get_meshes()
{
  const meshFiles = [];
  for (let i=0; i<map_objects.meshes.length; i++ )
  {
    meshFiles.push(my_path + '/meshes_obj/' + map_objects.meshes[i][1]);
  }
  for (let i=0; i<map_objects.meshes_private.length; i++ )
  {
    meshFiles.push(my_path + '/meshes_obj/' + map_objects.meshes_private[i][1]);
  }
  for (let i=0; i<map_objects.text_fnames.length; i++ )
  {
    meshFiles.push(my_path + '/meshes_obj/' + map_objects.text_fnames[i]);
  }
  for (let i=0; i<map_objects.text_fnames_private.length; i++ )
  {
    meshFiles.push(my_path + '/meshes_obj/' + map_objects.text_fnames_private[i]);
  }
  return meshFiles;
}


function install_callback(e)
{
    console.log('[Service Worker] Install');
    e.waitUntil((async () => {

      map_objects = await wait_json();
      console.log('map_objects res:', map_objects);
      version = map_objects.version;
      console.log('map_objects version:', version);
      cacheName = mapname + '-' + version;
      console.log('[Service Worker] cacheName:', cacheName);

      const meshFiles = get_meshes();

      const contentToCache = appShellFiles.concat(meshFiles);
      console.log('caching:', contentToCache);

      const cache = await caches.open(cacheName);
      console.log('[Service Worker] Caching all: app shell and content');
      await cache.addAll(contentToCache);
    })());
}


function fetch_callback(e)
{
    // console.log('fetch:', e.request.url);
    // Cache http and https only, skip unsupported chrome-extension:// and file://...
    if (!(
       e.request.url.startsWith('http:') || e.request.url.startsWith('https:')
    )) {
        return;
    }

  e.respondWith((async () => {
    console.log(`[Service Worker] Fetching resource: ${e.request.url}`);
    if( e.request.url.substring(e.request.url.length - 16)
        == 'map_objects.json')
    {
      // try without cache first, in order to reload after a version change
      // console.log('Fetching map_objects.json');
      try
      {
        const response = await fetch( e.request,
                                      {signal: AbortSignal.timeout(3000)} );
        const cache = await caches.open(cacheName);
        console.log(`[Service Worker] Caching new resource: ${e.request.url}`);
        cache.put(e.request, response.clone());
        return response;
      }
      catch( error )
      {
        console.log('Fetch failed, probable timeout:', error );
      }
    }

    const r = await caches.match(e.request);
    if (r) {
      // console.log(`[Service Worker] Cached: ${e.request.url}`);
      return r;
    }
    // console.log(`[Service Worker] Get: ${e.request.url}`);
    const response = await fetch(e.request);
    const cache = await caches.open(cacheName);
    console.log(`[Service Worker] Caching new resource: ${e.request.url}`);
    cache.put(e.request, response.clone());
    return response;
  })());
}


function activate_callback(e)
{
  console.log('activate');
  e.waitUntil(
    caches.keys().then((keyList) => {
      return Promise.all(
        keyList.map((key) => {
          if (key === cacheName) {
            return;
          }
          return caches.delete(key);
        }),
      );
    }),
  );
}


// Installing Service Worker
console.log('[Service Worker] Installing'); // , cacheName);
//       console.log('self:', self);
self.addEventListener('install', install_callback);

// Fetching content using Service Worker
self.addEventListener('fetch', fetch_callback);
console.log('fetch listener added');

self.addEventListener("activate", activate_callback);
console.log('activate listener added');

