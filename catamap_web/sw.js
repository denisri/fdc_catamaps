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
var offline_mode = false;

const appShellFiles = [
  my_path + '/help.html',
  my_path + '/index.html',
  my_path + '/map_objects.json',
  my_path + '/jquery.js',
  my_path + '/OrbitControls2.js',
  my_path + '/catamap.css',
  my_path + '/catamap_icon.png',
  my_path + '/catamap_webmanifest.json',
  my_path + '/screenshots/fdc_13_wide.webp',
  my_path + '/screenshots/fdc_13_narrow.webp',
  my_path + '/css/fonts/LMSansUltraCond10-Regular.ttf',
  my_path + '/css/fonts/VoieVerteFDC.ttf',
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


async function get_cache_name()
{
    // console.log('get_cache_name:', cacheName);
    if(cacheName != null)
      return cacheName;

    map_objects = await wait_json();
    // console.log('map_objects res:', map_objects);
    version = map_objects.version;
    // console.log('map_objects version:', version);
    cacheName = mapname + '-' + version;
    // console.log('[Service Worker] cacheName:', cacheName);
    cleanup_caches();
    return cacheName;
}


function install_callback(e)
{
    console.log('[Service Worker] Install');
    e.waitUntil((async () => {

      // map_objects = await wait_json();
      // // console.log('map_objects res:', map_objects);
      // version = map_objects.version;
      // console.log('map_objects version:', version);
      // cacheName = mapname + '-' + version;
      // console.log('[Service Worker] cacheName:', cacheName);
      await get_cache_name();
      // console.log('cacheName:', cacheName);
      // console.log('map_objects:', map_objects);

      const meshFiles = get_meshes();
      // console.log('meshes:', meshFiles);

      const contentToCache = appShellFiles.concat(meshFiles);
      // console.log('caching:', contentToCache);

      const cache = await caches.open(cacheName);
      console.log('[Service Worker] Caching all: app shell and content');
//       await cache.addAll(contentToCache);

      // to debug missing files
      const stack = [];
      contentToCache.forEach(file => stack.push(
          cache.add(file).catch(_=>console.error(`can't load ${file} to cache`))
      ));
      cleanup_caches();
      return Promise.all(stack);

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
    // const non_cached = ['map_objects.json', 'sw.js',
    //                     'catamap_webmanifest.json'];
    // console.log('cache:', cacheName);
    if(e.request.url.endsWith('map_objects.json') )
    {
      console.log('get out-of-cache', e.request.url);
      // try without cache first, in order to reload after a version change
      // console.log('Fetching map_objects.json');
      try
      {
        // const r = await caches.match(e.request);
        // if (r) {
        //   const cache = await caches.open(cacheName);
        //   // cache.delete(e.request);
        // }
        const response = await fetch( e.request,
                                      {signal: AbortSignal.timeout(3000)} );
        const c = response.clone();
        const map_objects = await response.json();
        // console.log('map_objects:', map_objects);
        const tmp_version = map_objects.version;
        console.log('map_objects version:', tmp_version);
        const tmp_cacheName = mapname + '-' + tmp_version;
        var reset_old_cahce = false;
        if(!caches.has(tmp_cacheName))
        {
          console.log(`[Service Worker] Caching new version ${tmp_cacheName}: ${e.request.url}`);
          reset_old_cahce = true;
        }
        cacheName = tmp_cacheName;
        version = tmp_version;
        const cache = await caches.open(cacheName);
        cache.put(e.request, c.clone());

        if(reset_old_cahce)
        {
          install_callback(e);
          activate_callback(e);
        }

        return c;
      }
      catch( error )
      {
        console.log('Fetch failed, probable timeout:', error );
        // if( r )
        // {
        //   cache.put(e.request, r);
        // }
      }
    }

    // look in the main cache first
    await get_cache_name();
    const cache = await caches.open(cacheName);
    // console.log('look in cache:', cacheName, ':', cache);
    const r = await cache.match(e.request);
    // console.log('r:', r);
    if (r && r.ok)
    {
      // console.log(`[Service Worker] Cached: ${e.request.url}`);
      return r;
    }
    // console.log('not in cache', e.request.url);

    const bck_cache_name = mapname + '-bak';
    const bck_cache = await caches.open(bck_cache_name);

    if(!offline_mode)
    {
      // now try to fetch quickly
      console.log(`[Service Worker] Get online: ${e.request.url}`);
      try
      {
        const response = await fetch(e.request,
                                    {signal: AbortSignal.timeout(30)});
        // console.log('response 2:', response);
        if(response && response.ok)
        {
          if(e.request.method == 'GET')
          {
            // OK cache it and return
            const cache = await caches.open(cacheName);
            console.log(`[Service Worker] Caching new resource in ${cacheName}: ${e.request.url}`);
            // console.log('e:', e);
            cache.add(e.request, response);
            // cache.put(e.request, response);
            // del from backup cache now it is in the main one
            bck_cache.delete(e.request);
          }
          return response;
        }
      }
      catch(err)
      {
        // console.log('error (timeout?):', err);
      }
    }

    // searh in backup caches
    // console.log('look in backup cache', bck_cache_name, ':', bck_cache);
    const r2 = await bck_cache.match(e.request);

    if(!r2 && !offline_mode)
    {
      // console.log('not in backup cache.');
      // try harder to fetch from network
      const r3 = await fetch(e.request);
      // console.log('r3:', r3);
      // cache it and return
      const cache = await caches.open(cacheName);
      console.log(`[Service Worker] Caching new resource in ${cacheName} after 2nd attempt: ${e.request.url}`);
      if(e.request.method == 'GET')
      {
        cache.add(e.request, r3);
        // del from backup cache now it is in the main one
        bck_cache.delete(e.request);
      }
      return r3;
    }
    // else
    //   console.log('found in backup cache.');

    // here we assume we are now offline
    offline_mode = true;

    return r2;

  })());
}


async function moveCacheData(oldCacheName, newCacheName, backupCacheName)
{
  const oldCache = await caches.open(oldCacheName);
  const newCache = await caches.open(newCacheName);
  const backupCache = await caches.open(backupCacheName);
  console.log('[Service Worker] moving old cache:', oldCacheName,
              ' to:', backupCacheName);

  // Récupère toutes les requêtes du cache source
  const requests = await oldCache.keys();

  // Copie chaque paire requête/réponse vers le backup cache cache
  for (const request of requests)
  {
    // but only if it is not in the new cache
    const response = await newCache.match(request);
    if (!response)
    {
      const response = await oldCache.match(request);
      if (response)
      {
        await backupCache.put(request, response);
      }
    }
  }

  console.log('[Service Worker] delete cache:', oldCacheName, ' for new:',
              newCacheName);
  // Supprime l'ancien cache une fois la copie terminée
  await caches.delete(oldCacheName);
}


async function cleanup_caches()
{
  console.log('[Service Worker] cleanup caches');
  // console.log('caches:', await caches.keys());
  get_cache_name();

  caches.keys().then((keyList) => {
    return Promise.all(
      keyList.map((key) => {
        if (key === cacheName || key === mapname + '-bak'
            || !key.startsWith(mapname + '-'))
        {
          return;
        }
        moveCacheData(key, cacheName, mapname + '-bak');
        // console.log('[Service Worker] delete cache:', key, ' from:', cacheName);
        // return caches.delete(key);
      })
    );
  });
}



function activate_callback(e)
{
  console.log('activate');
  // console.log('caches:', await caches.keys());
  // e.waitUntil(
  //   caches.keys().then((keyList) => {
  //     get_cache_name();
  //     return Promise.all(
  //       keyList.map((key) => {
  //         if (key === cacheName || key === mapname + '-bak'
  //           || !key.startsWith(mapname + '-'))
  //         {
  //           return;
  //         }
  //         moveCacheData(key, cacheName, mapname + '-bak');
  //         // console.log('[Service Worker] delete cache:', key, ' from:', cacheName);
  //         // return caches.delete(key);
  //       }),
  //     );
  //   }),
  // );
}



// // Installing Service Worker
console.log('[Service Worker] Installing');
//       console.log('self:', self);
self.addEventListener('install', install_callback);

// Fetching content using Service Worker
self.addEventListener('fetch', fetch_callback);
console.log('fetch listener added');

self.addEventListener("activate", activate_callback);
console.log('activate listener added');
